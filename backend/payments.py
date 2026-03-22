import razorpay
import os
from typing import Optional
import hmac
import hashlib
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

# Razorpay client initialization
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        logger.info("Razorpay client initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Razorpay client: {e}")

def create_order(amount: int, currency: str = "INR", receipt: str = "order_1", user_id: Optional[int] = None, plan: str = "pro"):
    """
    Create a Razorpay order. Amount in paise (₹1 = 100 paise).
    """
    if not client:
        raise HTTPException(status_code=500, detail="Razorpay client not configured")
    try:
        order_data = {
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
        
        order = client.order.create(order_data)
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
    secret = RAZORPAY_KEY_SECRET.encode()
    expected = hmac.new(secret, msg.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

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

def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    Alias for verify_razorpay_signature.
    """
    return verify_razorpay_signature(order_id, payment_id, signature)

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
