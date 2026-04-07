# backend/services/payments/logic.py
import os
import uuid
import hmac
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException

from backend.db.firebase import db as firestore_db
from backend.db.redis import (
    incr_daily_ai_spend, 
    get_daily_ai_spend, 
    distributed_lock, 
    r as redis_client, 
    HAS_REDIS
)
from backend.config.system import TIERS, COST_MATRIX

logger = logging.getLogger(__name__)

# Razorpay client initialization
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

_razorpay_client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        import razorpay # type: ignore
        _razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        logger.info("Razorpay client initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Razorpay client: {e}")

def create_order(amount: int, user_id: str, plan: str):
    if not _razorpay_client:
        raise HTTPException(status_code=500, detail="Payments not configured.")
    try:
        order_data = {
            "amount": amount,
            "currency": "INR",
            "receipt": f"receipt_{uuid.uuid4().hex[:6]}",
            "notes": {"user_id": user_id, "plan": plan}
        }
        return _razorpay_client.order.create(order_data)
    except Exception as e:
        logger.error(f"Order creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate payment.")

def verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    if not RAZORPAY_KEY_SECRET: return False
    try:
        msg = f"{order_id}|{payment_id}"
        expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False

def use_credits(user_id: str, action: str = "chat", amount: Optional[int] = None):
    """Atomic credit deduction logic."""
    cost = amount if amount is not None else COST_MATRIX.get(action, 1)
    
    # Fast path: daily allowance
    daily_spend = get_daily_ai_spend(user_id)
    
    with distributed_lock(f"credits:{user_id}", ttl=10) as acquired:
        if not acquired:
            raise HTTPException(status_code=429, detail="Transaction locking failed.")
            
        user_ref = firestore_db.collection("users").document(user_id)
        user_doc = user_ref.get()
        if not user_doc.exists: raise HTTPException(status_code=404, detail="User missing.")
        
        user_data = user_doc.to_dict()
        tier = user_data.get("tier", "free")
        limit = TIERS.get(tier, TIERS["free"])["daily_limit"]
        
        # Priority 1: Free daily limit
        if daily_spend + cost <= limit:
            incr_daily_ai_spend(user_id, float(cost))
            return {"status": "success", "source": "allowance"}

        # Priority 2: Paid credits
        credits = int(user_data.get("credits", 0))
        if credits < cost:
            raise HTTPException(status_code=402, detail="Insufficient credits and limit reached.")
            
        new_credits = credits - cost
        user_ref.update({"credits": new_credits})
        if HAS_REDIS: redis_client.setex(f"user_credits:{user_id}", 300, new_credits)
        
        return {"status": "success", "source": "credits", "balance": new_credits}

def upgrade_user_tier(user_id: str, plan: str):
    bonus = 100 if plan == "pro" else 500 if plan == "creator" else 0
    user_ref = firestore_db.collection("users").document(user_id)
    doc = user_ref.get()
    if doc.exists:
        old_credits = doc.to_dict().get("credits", 0)
        user_ref.update({
            "tier": plan,
            "credits": old_credits + bonus,
            "upgraded_at": datetime.now(timezone.utc)
        })
        return True
    return False
