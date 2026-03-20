import stripe
import os
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
try:
    from backend.db import get_db
    from backend.models import Users
    from backend.auth import get_current_user
except ImportError:
    from db import get_db
    from models import Users
    from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])

# Stripe configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    logger.info("Stripe initialized.")

PLANS = {
    "pro":     os.getenv("STRIPE_PRO_PRICE_ID", "price_xxxxxxxxxxxxx"),  # ₹499/month
    "creator": os.getenv("STRIPE_CREATOR_PRICE_ID", "price_xxxxxxxxxxxxx"),  # ₹1499/month
}

@router.post("/create_checkout")
async def create_checkout(plan: str, db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    """
    Creates a Stripe Checkout Session for subscription.
    """
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured")
        
    if plan not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan selected")

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8080")
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PLANS[plan], "quantity": 1}],
            mode="subscription",
            success_url=f"{frontend_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_url}/pricing",
            metadata={"user_id": current_user.id, "plan": plan}
        )
        return {"url": session.url}
    except Exception as e:
        logger.error(f"Stripe checkout session creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stripe_webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhooks for successful payments.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event.type == "checkout.session.completed":
        session = event.data.object
        user_id = session.metadata.get("user_id")
        plan = session.metadata.get("plan")
        if user_id and plan:
            upgrade_user_tier(int(user_id), plan, db)
            logger.info(f"Payment successful: User {user_id} upgraded to {plan}")

    return {"status": "success"}

def upgrade_user_tier(user_id: int, plan: str, db: Session):
    """
    Upgrades a user's tier in the database after successful payment.
    """
    user = db.query(Users).filter(Users.id == user_id).first()
    if user:
        user.tier = plan
        # Grant bonus credits for upgrading
        if plan == "pro":
            user.credits = (user.credits or 0) + 100
        elif plan == "creator":
            user.credits = (user.credits or 0) + 500
        db.commit()
        logger.info(f"User {user_id} upgraded to {plan}")
        return True
    return False

def use_credits(user_id: int, amount: int, db: Session):
    """
    Deducts credits from a user's account.
    """
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.tier == "free" and (user.credits or 0) < amount:
        raise HTTPException(status_code=402, detail="Insufficient credits. Upgrade to Pro for more generations.")
    
    user.credits = (user.credits or 0) - amount
    db.commit()
    return user.credits
