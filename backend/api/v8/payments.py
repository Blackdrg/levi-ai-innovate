"""
Sovereign Payments API v8.
Financial and Credit management for the LEVI-AI OS.
Refactored from v1 to V8 Sovereign standard.
"""

import os
import hmac
import hashlib
import logging
import razorpay
from typing import Any
from fastapi import APIRouter, HTTPException, Depends
from backend.api.utils.auth import get_current_user
from backend.db.firebase import db as firestore_db
from backend.config.system import TIERS
from backend.db.redis import get_daily_ai_spend
from firebase_admin import firestore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Payments V8"])

# --- Razorpay Initialization ---
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        logger.info("[Payments-V8] Razorpay Client: Active.")
    except Exception as e:
        logger.error(f"[Payments-V8] Razorpay Initialization Failed: {e}")

@router.post("/verify")
async def verify_payment_endpoint(
    payload: dict,
    current_user: Any = Depends(get_current_user)
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
        
    # Signature verification
    msg = f"{order_id}|{payment_id}"
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode("utf-8"), 
        msg.encode("utf-8"), 
        digestmod=hashlib.sha256
    ).hexdigest()
    
    if hmac.compare_digest(expected, signature):
        user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
        bonus = 100 if plan == "pro" else 500 if plan == "creator" else 0
        
        firestore_db.collection("users").document(user_id).update({
            "tier": plan,
            "credits": firestore.Increment(bonus),
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        logger.info(f"[Payments-V8] User {user_id} upgraded to {plan}")
        return {"status": "success", "message": "Transaction verified."}
    else:
        raise HTTPException(status_code=400, detail="Invalid payment resonance.")

@router.get("/allowance")
async def get_allowance_status(current_user: Any = Depends(get_current_user)):
    """ Returns the user's remaining daily AI allowance. """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    # Logic from v1 merged here
    user_ref = firestore_db.collection("users").document(user_id)
    doc = user_ref.get()
    user_data = doc.to_dict() if doc.exists else {}
    
    tier = user_data.get("tier", "free")
    limit = TIERS.get(tier, TIERS["free"])["daily_limit"]
    spend = get_daily_ai_spend(user_id)
    
    return {
        "tier": tier,
        "remaining": max(0, limit - spend),
        "limit": limit,
        "credits": user_data.get("credits", 0)
    }
