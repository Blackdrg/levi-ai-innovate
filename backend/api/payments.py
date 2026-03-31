"""
backend/api/payments.py

Financial and Credit API - Handles Razorpay orders, verification, and credit logic.
Refactored from backend/payments.py.
"""

import os
import hmac
import hashlib
import logging
import razorpay
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request
from backend.firestore_db import db as firestore_db
from backend.auth import get_current_user_optional
from backend.config import TIERS, COST_MATRIX
from backend.redis_client import incr_daily_ai_spend, get_daily_ai_spend, distributed_lock, HAS_REDIS
from backend.utils.exceptions import LEVIException
from backend.utils.robustness import standard_retry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Payments"])

# --- Razorpay Initialization ---
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        logger.info("Razorpay Client: Active.")
    except Exception as e:
        logger.error(f"Razorpay Initialization Failed: {e}")

# --- Logic Layer ---

def verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """ Validates the payment's cryptographic signature. """
    if not RAZORPAY_KEY_SECRET: return False
    try:
        msg = f"{order_id}|{payment_id}"
        expected = hmac.new(
            RAZORPAY_KEY_SECRET.encode("utf-8"), 
            msg.encode("utf-8"), 
            digestmod=hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False

def use_credits(user_id: str, action: str = "chat", amount: Optional[int] = None):
    """
    Deducts AI units or credits from a user's account.
    Prioritizes Tier Allowance -> Credits fallback.
    """
    cost = amount if amount is not None else COST_MATRIX.get(action, 1)
    user_ref = firestore_db.collection("users").document(user_id)
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        raise LEVIException("User entity not found.", status_code=404)
        
    user_data = user_doc.to_dict()
    tier = user_data.get("tier", "free")
    current_credits = int(user_data.get("credits", 0))
    limit = TIERS.get(tier, TIERS["free"])["daily_limit"]
    
    # 1. Tier Allowance Check
    daily_spend = get_daily_ai_spend(user_id)
    if daily_spend + cost <= limit:
        incr_daily_ai_spend(user_id, float(cost))
        return {"status": "success", "source": "allowance"}

    # 2. Credits Fallback (Locked)
    if not HAS_REDIS:
         raise LEVIException("Credit transaction requires Redis.", status_code=503)

    with distributed_lock(f"credits:{user_id}", ttl=10) as acquired:
        if not acquired:
            raise LEVIException("Transaction in progress.", status_code=429)
            
        if current_credits < cost:
            raise LEVIException("Insufficient cosmic credits.", status_code=402)
        
        new_credits = current_credits - cost
        user_ref.update({"credits": new_credits})
        return {"status": "success", "source": "credits", "balance": new_credits}

# --- Endpoints ---

@router.post("/verify")
@router.post("/verify_payment")
async def verify_payment_endpoint(
    payload: dict,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Verifies a Razorpay payment and upgrades the user's tier.
    """
    order_id = payload.get("razorpay_order_id")
    payment_id = payload.get("razorpay_payment_id")
    signature = payload.get("razorpay_signature")
    plan = payload.get("plan", "pro")
    
    if not all([order_id, payment_id, signature]):
        raise HTTPException(status_code=400, detail="Missing payment telemetry.")
        
    if verify_razorpay_signature(order_id, payment_id, signature):
        if current_user:
            user_id = current_user["uid"]
            bonus = 100 if plan == "pro" else 500 if plan == "creator" else 0
            firestore_db.collection("users").document(user_id).update({
                "tier": plan,
                "credits": google_firestore.Increment(bonus)
            })
            logger.info(f"User {user_id} upgraded to {plan}")
        return {"status": "success", "message": "Transaction verified. Field upgraded."}
    else:
        raise HTTPException(status_code=400, detail="Invalid payment resonance.")

@router.get("/allowance")
async def get_allowance_status(current_user: dict = Depends(get_current_user_optional)):
    """ Returns the user's remaining daily AI allowance. """
    if not current_user:
        return {"tier": "guest", "remaining": 0, "limit": 0}
    
    uid = current_user["uid"]
    tier = current_user.get("tier", "free")
    limit = TIERS.get(tier, TIERS["free"])["daily_limit"]
    spend = get_daily_ai_spend(uid)
    
    return {
        "tier": tier,
        "remaining": max(0, limit - spend),
        "limit": limit,
        "credits": current_user.get("credits", 0)
    }
