# pyright: reportMissingImports=false
import razorpay  # type: ignore
import os
from typing import Optional
import hmac
import hashlib
import logging
from fastapi import APIRouter, HTTPException, Depends, Request  # type: ignore
from backend.firestore_db import db as firestore_db  # type: ignore
from backend.redis_client import _get, _set, HAS_REDIS  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])

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
        return False
    msg = f"{order_id}|{payment_id}"
    secret_bytes = RAZORPAY_KEY_SECRET.encode()
    expected = hmac.new(
        secret_bytes, 
        msg.encode() if isinstance(msg, str) else msg, 
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

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

def use_credits(user_id: str, amount: int):
    """
    Deducts credits from a user's account in Firestore.
    """
    user_ref = firestore_db.collection("users").document(user_id)
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
        
    data = user_doc.to_dict()
    current_credits = int(data.get("credits", 0))
    tier = data.get("tier", "free")
    
    if tier == "free" and current_credits < amount:
        raise HTTPException(status_code=402, detail="Insufficient credits. Upgrade to Pro for more generations.")
    
    new_credits = current_credits - amount
    user_ref.update({"credits": new_credits})
    return new_credits

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
