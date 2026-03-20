import os
import stripe
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

try:
    from backend.db import get_db
    from backend.models import Users
except ImportError:
    from db import get_db
    from models import Users

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Stripe config — set these in your .env
# ─────────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET  = os.getenv("STRIPE_WEBHOOK_SECRET")

# After creating products in Stripe dashboard, paste Price IDs here
PRICE_IDS = {
    "pro":     os.getenv("STRIPE_PRICE_PRO",     "price_REPLACE_WITH_PRO_PRICE_ID"),
    "creator": os.getenv("STRIPE_PRICE_CREATOR", "price_REPLACE_WITH_CREATOR_PRICE_ID"),
}

# Credits granted per tier per month
TIER_CREDITS = {
    "free":    10,
    "pro":     300,
    "creator": 999999,  # Unlimited effectively
}

router = APIRouter(prefix="/payments", tags=["payments"])


# ─────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────
class CheckoutRequest(BaseModel):
    plan: str        # "pro" or "creator"
    user_id: int


class PortalRequest(BaseModel):
    user_id: int


# ─────────────────────────────────────────────
# Helper: upgrade user tier in DB
# ─────────────────────────────────────────────
def upgrade_user_tier(user_id: int, plan: str, stripe_customer_id: str, db: Session):
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        logger.error(f"upgrade_user_tier: user {user_id} not found")
        return
    user.tier               = plan
    user.credits            = TIER_CREDITS.get(plan, 10)
    user.stripe_customer_id = stripe_customer_id
    db.commit()
    logger.info(f"User {user_id} upgraded to {plan}")


def downgrade_user_tier(stripe_customer_id: str, db: Session):
    user = db.query(Users).filter(
        Users.stripe_customer_id == stripe_customer_id
    ).first()
    if not user:
        return
    user.tier    = "free"
    user.credits = TIER_CREDITS["free"]
    db.commit()
    logger.info(f"User {user.id} downgraded to free")


# ─────────────────────────────────────────────
# Helper: deduct credits (call before generation)
# ─────────────────────────────────────────────
def use_credits(user_id: int, amount: int, db: Session):
    """
    Raises HTTP 402 if free user runs out of credits.
    Pro/Creator users are never blocked.
    """
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        return  # Anonymous request — let it through

    if user.tier in ("pro", "creator"):
        return  # Unlimited

    if (user.credits or 0) < amount:
        raise HTTPException(
            status_code=402,
            detail={
                "error":   "out_of_credits",
                "message": "You've used your free credits. Upgrade to Pro for unlimited generations.",
                "upgrade": "/pricing"
            }
        )
    user.credits = (user.credits or 0) - amount
    db.commit()


# ─────────────────────────────────────────────
# Route 1: Create Checkout Session
# ─────────────────────────────────────────────
@router.post("/create_checkout")
async def create_checkout(req: CheckoutRequest, db: Session = Depends(get_db)):
    if req.plan not in PRICE_IDS:
        raise HTTPException(400, "Invalid plan. Choose 'pro' or 'creator'.")

    if not stripe.api_key:
        raise HTTPException(500, "Stripe is not configured on this server.")

    user = db.query(Users).filter(Users.id == req.user_id).first()
    if not user:
        raise HTTPException(404, "User not found.")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PRICE_IDS[req.plan], "quantity": 1}],
            mode="subscription",
            customer_email=getattr(user, "email", None),
            success_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:8080')}/success.html?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:8080')}/pricing.html",
            metadata={"user_id": str(req.user_id), "plan": req.plan},
        )
        return {"checkout_url": session.url, "session_id": session.id}

    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(500, str(e))


# ─────────────────────────────────────────────
# Route 2: Customer Portal (manage/cancel sub)
# ─────────────────────────────────────────────
@router.post("/customer_portal")
async def customer_portal(req: PortalRequest, db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.id == req.user_id).first()
    if not user or not getattr(user, "stripe_customer_id", None):
        raise HTTPException(404, "No billing account found.")

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:8080')}/index.html",
    )
    return {"portal_url": session.url}


# ─────────────────────────────────────────────
# Route 3: Stripe Webhook
# ─────────────────────────────────────────────
@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not WEBHOOK_SECRET:
        raise HTTPException(500, "Webhook secret not configured.")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        logger.warning("Invalid Stripe webhook signature")
        raise HTTPException(400, "Invalid signature")

    event_type = event["type"]
    data       = event["data"]["object"]
    logger.info(f"Stripe event received: {event_type}")

    # ── Payment succeeded → upgrade user ──
    if event_type == "checkout.session.completed":
        user_id  = int(data["metadata"].get("user_id", 0))
        plan     = data["metadata"].get("plan", "pro")
        customer = data.get("customer", "")
        if user_id:
            upgrade_user_tier(user_id, plan, customer, db)

    # ── Subscription renewed → refresh credits ──
    elif event_type == "invoice.payment_succeeded":
        customer = data.get("customer")
        # Find user by stripe_customer_id and reset credits
        user = db.query(Users).filter(
            Users.stripe_customer_id == customer
        ).first()
        if user:
            user.credits = TIER_CREDITS.get(user.tier, 10)
            db.commit()
            logger.info(f"Credits refreshed for user {user.id}")

    # ── Subscription cancelled → downgrade ──
    elif event_type in ("customer.subscription.deleted", "invoice.payment_failed"):
        customer = data.get("customer")
        downgrade_user_tier(customer, db)

    return JSONResponse({"status": "ok"})


# ─────────────────────────────────────────────
# Route 4: Buy Credit Pack (one-time)
# ─────────────────────────────────────────────
CREDIT_PACKS = {
    "small":  {"credits": 50,  "price_id": os.getenv("STRIPE_PRICE_CREDITS_SMALL",  "price_REPLACE")},
    "medium": {"credits": 200, "price_id": os.getenv("STRIPE_PRICE_CREDITS_MEDIUM", "price_REPLACE")},
}

class CreditPackRequest(BaseModel):
    pack: str    # "small" or "medium"
    user_id: int

@router.post("/buy_credits")
async def buy_credits(req: CreditPackRequest, db: Session = Depends(get_db)):
    pack = CREDIT_PACKS.get(req.pack)
    if not pack:
        raise HTTPException(400, "Invalid pack.")

    user = db.query(Users).filter(Users.id == req.user_id).first()
    if not user:
        raise HTTPException(404, "User not found.")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": pack["price_id"], "quantity": 1}],
        mode="payment",   # One-time, not subscription
        success_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:8080')}/success.html",
        cancel_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:8080')}/pricing.html",
        metadata={"user_id": str(req.user_id), "credits": str(pack["credits"])},
    )
    return {"checkout_url": session.url}
