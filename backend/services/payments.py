# pyright: reportMissingImports=false
import razorpay  # type: ignore
import os
from typing import Optional
import hmac
import hashlib
import logging
from fastapi import APIRouter, HTTPException, Depends, Request  # type: ignore
from backend.db.firestore_db import db as firestore_db  # type: ignore
from backend.db.redis_client import _get, _set, HAS_REDIS  # type: ignore
from backend.auth import get_current_user_optional  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["payments"])

# Razorpay client initialization
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        logger.info("Razorpay client initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Razorpay client. Check RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET: {e}")

from typing import Optional, Any


TIER_CREDITS = {
    "free": 10,
    "pro": 100,
    "creator": 500,
}


def get_tier_credits(tier: str) -> int:
    """Return the monthly credit allowance for a given tier."""
    return TIER_CREDITS.get(tier, 10)


def create_order(amount: int, currency: str = "INR", receipt: str = "order_1", user_id: Optional[str] = None, plan: str = "pro"):
    """
    Create a Razorpay order. Amount in paise (₹1 = 100 paise).
    """
    if not client:
        raise HTTPException(status_code=500, detail="Razorpay client not configured")
    try:
        from typing import Dict, Any
        order_data: Dict[str, Any] = {
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1
        }
        if user_id and plan:
            order_data["notes"] = {
                "user_id": user_id,
                "plan": plan
            }
        
        # Use getattr to avoid Pylance error with dynamic attributes in razorpay-python
        order = getattr(client, "order").create(order_data)
        return order
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    Verify the payment signature from the frontend callback.
    """
    if not RAZORPAY_KEY_SECRET:
        logger.error("RAZORPAY_KEY_SECRET not configured")
        return False
    
    try:
        msg = f"{order_id}|{payment_id}"
        secret_bytes = RAZORPAY_KEY_SECRET.encode("utf-8")
        data_bytes = msg.encode("utf-8")
        
        expected = hmac.new(
            secret_bytes, 
            data_bytes, 
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    except Exception as e:
        logger.error(f"Razorpay signature verification failed: {e}")
        return False

def upgrade_user_tier(user_id: str, plan: str):
    """
    Upgrades a user's tier in Firestore after successful payment.
    """
    user_ref = firestore_db.collection("users").document(user_id)
    user_doc = user_ref.get()
    
    if user_doc.exists:
        data = user_doc.to_dict()
        current_credits = data.get("credits", 0)
        
        bonus = 100 if plan == "pro" else 500 if plan == "creator" else 0
        new_credits = current_credits + bonus
        
        user_ref.update({
            "tier": plan,
            "credits": new_credits
        })
        logger.info(f"User {user_id} upgraded to {plan}")
        return True
    return False

def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    Alias for verify_razorpay_signature.
    """
    return verify_razorpay_signature(order_id, payment_id, signature)

from backend.config import TIERS, COST_MATRIX
from backend.db.redis_client import incr_daily_ai_spend, get_daily_ai_spend # type: ignore

def use_credits(user_id: str, action: str = "chat", amount: Optional[int] = None):
    """
    Deducts AI units or credits from a user's account with absolute atomicity.
    Prioritizes Tier Allowance (Redis) -> Credits Fallback (Firestore Transaction + Distributed Lock).
    """
    from backend.db.redis_client import distributed_lock # type: ignore
    
    # 1. Determine Cost
    cost = amount if amount is not None else COST_MATRIX.get(action, 1)
    
    # 2. Check Daily Spend (Fast Path via Redis)
    # This is fine to do before the lock as incr_daily_ai_spend is atomic in Redis.
    daily_spend = get_daily_ai_spend(user_id)
    
    # Fetch tier from Redis/Memory if possible, but we need the limit
    # We'll do a quick check here, and a final check inside the lock for credits.
    # To be safe and avoid multi-reads, we'll acquire the lock first for the fallback case.
    
    # 3. Distributed Lock for Credit Operations
    with distributed_lock(f"credits:{user_id}", ttl=15, retries=3, backoff=0.2) as acquired:
        if not acquired:
            logger.warning(f"Credit lock timeout for {user_id}")
            raise HTTPException(status_code=429, detail="Transaction in progress. Please retry.")
            
        try:
            # 4. Refresh User Data INSIDE the lock
            user_ref = firestore_db.collection("users").document(user_id)
            user_doc = user_ref.get()
            if not user_doc.exists:
                raise HTTPException(status_code=404, detail="User not found")
                
            user_data = user_doc.to_dict()
            tier = user_data.get("tier", "free")
            current_credits = int(user_data.get("credits", 0))
            limit = TIERS.get(tier, TIERS["free"])["daily_limit"]
            
            # 5. Final Allowance Check (Re-check spend inside lock if needed)
            if daily_spend + cost <= limit:
                incr_daily_ai_spend(user_id, float(cost))
                return {"status": "success", "source": "allowance", "remaining_limit": limit - (daily_spend + cost)}

            # 6. Final Credit Check
            if current_credits < cost:
                raise HTTPException(
                    status_code=402, 
                    detail=f"Daily limit ({limit}) reached. Insufficient credits ({current_credits}) for additional usage."
                )
            
            # 7. Atomic Update
            new_credits = current_credits - cost
            user_ref.update({"credits": new_credits})
            
            # 8. Cache the new credit value in Redis for faster subsequent reads
            from backend.db.redis_client import r as redis_client, HAS_REDIS
            if HAS_REDIS:
                redis_client.setex(f"user_credits:{user_id}", 300, new_credits)

            return {"status": "success", "source": "credits", "remaining_credits": new_credits}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Atomic credit transaction failed: {e}")
            raise HTTPException(status_code=500, detail="Transaction failed")

def process_subscription_lapse(user_id: str):
    """
    Downgrade a user to 'free' tier and cap credits at 10 in Firestore.
    """
    try:
        user_ref = firestore_db.collection("users").document(user_id)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            data = user_doc.to_dict()
            if data.get("tier") != "free":
                logger.info(f"Subscription lapsed for user {user_id}. Downgrading to free tier.")
                update_data = {"tier": "free"}
                if data.get("credits", 0) > 10:
                    update_data["credits"] = 10
                user_ref.update(update_data)
                return True
    except Exception as e:
        logger.error(f"Failed to process subscription lapse for user {user_id}: {e}")
    return False

@router.post("/verify_payment")
async def verify_payment_endpoint(
    payload: dict,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Router endpoint for Razorpay payment verification."""
    order_id = payload.get("razorpay_order_id")
    payment_id = payload.get("razorpay_payment_id")
    signature = payload.get("razorpay_signature")
    plan = payload.get("plan", "pro")
    
    if not order_id or not payment_id or not signature:
        raise HTTPException(status_code=400, detail="Missing payment identifiers")
        
    if verify_razorpay_signature(order_id, payment_id, signature):
        if current_user:
            upgrade_user_tier(current_user["uid"], plan)
        return {"status": "success", "message": "Payment verified and account upgraded"}
    else:
        raise HTTPException(status_code=400, detail="Invalid payment signature")
