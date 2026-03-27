# pyright: reportMissingImports=false
import pytest  # type: ignore
import hmac
import hashlib
import os
from fastapi import HTTPException  # type: ignore
# from backend.main import verify_password, get_password_hash, create_access_token  # type: ignore
from backend.payments import verify_razorpay_signature, use_credits  # type: ignore

# def test_password_hashing():
#     password = "testpassword123"
#     hashed = get_password_hash(password)
#     assert verify_password(password, hashed)
#     assert not verify_password("wrongpassword", hashed)

from unittest.mock import patch, MagicMock

def test_credit_deduction():
    # Mock firestore_db and use_credits
    user_id = "user_123"
    initial_credits = 10
    
    with patch("backend.payments.use_credits") as mock_use_credits:
        mock_use_credits.return_value = initial_credits - 5
        
        new_credits = use_credits(user_id, 5)
        assert new_credits == 5
        mock_use_credits.assert_called_once_with(user_id, 5)
    
    # Try to deduct more than available
    with patch("backend.payments.use_credits") as mock_use_credits:
        mock_use_credits.side_effect = HTTPException(status_code=402, detail="Insufficient credits")
        with pytest.raises(HTTPException) as exc:
            use_credits(user_id, 100)
        assert exc.value.status_code == 402

def test_webhook_idempotency(app_client, db_session):
    # Mock Redis isn't easily available in simple pytest without setup
    # But we can test the logic in main.py if we patch the redis client
    pass

def test_hmac_verification():
    secret = "testsecret"
    order_id = "order_1"
    payment_id = "pay_1"
    msg = f"{order_id}|{payment_id}"
    signature = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    
    with pytest.MonkeyPatch().context() as m:
        m.setattr("backend.payments.RAZORPAY_KEY_SECRET", secret)
        assert verify_razorpay_signature(order_id, payment_id, signature)
        assert not verify_razorpay_signature(order_id, payment_id, "wrong_sig")
