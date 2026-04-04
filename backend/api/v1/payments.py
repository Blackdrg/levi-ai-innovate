"""
backend/api/v1/payments.py

Financial and Credit API - Handles Razorpay orders, verification, and credit logic.
Refactored from backend/payments.py.
"""

import os
import hmac
import hashlib
import logging
import razorpay
import json
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request
from backend.db.postgres_db import get_read_session, get_write_session
from sqlalchemy import text
from backend.auth.logic import get_current_user_optional
from backend.config.system import TIERS, COST_MATRIX
from backend.db.redis import incr_daily_ai_spend, get_daily_ai_spend, distributed_lock, HAS_REDIS
from backend.utils.exceptions import LEVIException
from backend.utils.robustness import standard_retry
from backend.broadcast_utils import SovereignBroadcaster

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

@standard_retry(attempts=3)
async def use_credits(user_id: str, action: str = "chat", amount: Optional[int] = None):
    """
    Deducts credits from a user's account via the Postgres SQL Fabric.
    Prioritizes Tier Allowance -> Credits fallback.
    """
    cost = amount if amount is not None else COST_MATRIX.get(action, 1) or 1
    
    # 1. SQL Identity Fetch
    async with get_read_session() as session:
        query = text("SELECT subscription_tier, credits FROM user_profiles WHERE uid = :uid")
        res = await session.execute(query, {"uid": user_id})
        user_data = res.mappings().one_or_none()
    
    if not user_data:
        raise LEVIException("User profile not found in Monolith SQL fabric.", status_code=404)
        
    tier = user_data["subscription_tier"] or "free"
    current_credits = user_data["credits"] or 0
    limit = TIERS.get(tier, TIERS["free"])["daily_limit"]
    
    # 2. Tier Allowance Check (Fast Path - Redis)
    daily_spend = get_daily_ai_spend(user_id)
    if daily_spend + cost <= limit:
        incr_daily_ai_spend(user_id, float(cost))
        return {"status": "success", "source": "allowance"}

    # 3. Credits Fallback (Atomic SQL Transaction)
    if current_credits < cost:
        raise LEVIException(f"Insufficient cosmic credits. ({current_credits} < {cost})", status_code=402)
    
    async with get_write_session() as session:
        await session.execute(
            text("UPDATE user_profiles SET credits = credits - :cost, updated_at = CURRENT_TIMESTAMP WHERE uid = :uid"),
            {"uid": user_id, "cost": cost}
        )
        
    return {"status": "success", "source": "credits", "balance": current_credits - cost}

# --- Endpoints ---

@router.post("/verify")
@standard_retry(attempts=3)
async def verify_payment_endpoint(
    payload: dict,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Verifies a Razorpay payment and upgrades the user's tier in the SQL Fabric.
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
            
            # 1. v13.0 SQL Resonance Update (Absolute Monolith)
            try:
                async with get_write_session() as session:
                    await session.execute(
                        text("""
                            INSERT INTO user_profiles (uid, subscription_tier, credits, updated_at)
                            VALUES (:uid, :tier, :bonus, CURRENT_TIMESTAMP)
                            ON CONFLICT (uid) DO UPDATE SET
                            subscription_tier = EXCLUDED.subscription_tier,
                            credits = user_profiles.credits + EXCLUDED.credits,
                            updated_at = CURRENT_TIMESTAMP
                        """),
                        {"uid": user_id, "tier": plan, "bonus": bonus}
                    )
            except Exception as e:
                logger.error(f"[Payments-v13] SQL Mirroring failure: {e}")
                raise HTTPException(status_code=500, detail="Monolith SQL persistence failure.")

            # 2. Financial Pulse (Broadcaster Bridge)
            pulse = {
                "type": "FINANCIAL_RESONANCE",
                "plan": plan,
                "bonus": bonus,
                "message": f"Celestial Upgrade confirmed: {plan.upper()} tier established."
            }
            SovereignBroadcaster.broadcast(pulse)

            logger.info(f"User {user_id} upgraded to {plan} (100% SQL Sovereign)")
        return {"status": "success", "message": "Transaction verified. Absolute Monolith updated."}
    else:
        raise HTTPException(status_code=400, detail="Invalid payment resonance.")

@router.get("/allowance")
async def get_allowance_status(current_user: dict = Depends(get_current_user_optional)):
    """ Returns the user's remaining daily AI allowance from the Monolith SQL Fabric. """
    if not current_user:
        return {"tier": "guest", "remaining": 0, "limit": 0}
    
    uid = current_user["uid"]
    
    # Fetch from SQL
    async with get_read_session() as session:
        res = await session.execute(
            text("SELECT subscription_tier, credits FROM user_profiles WHERE uid = :uid"),
            {"uid": uid}
        )
        data = res.mappings().one_or_none()
        
    tier = data["subscription_tier"] if data else "free"
    credits = data["credits"] if data else 0
    limit = TIERS.get(tier, TIERS["free"])["daily_limit"]
    spend = get_daily_ai_spend(uid)
    
    return {
        "tier": tier,
        "remaining": max(0, limit - spend),
        "limit": limit,
        "credits": credits
    }
