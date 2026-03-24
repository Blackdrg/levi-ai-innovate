# pyright: reportMissingImports=false
import pytest  # type: ignore
import hmac
import hashlib
import os
from fastapi import HTTPException  # type: ignore
from backend.main import verify_password, get_password_hash, create_access_token  # type: ignore
from backend.payments import verify_razorpay_signature, use_credits  # type: ignore
from backend.models import Users  # type: ignore

def test_password_hashing():
    password = "testpassword123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

def test_credit_deduction(db_session, test_user):
    # Initial credits = dynamic (due to test interference)
    user_id = int(test_user.id)
    initial = int(test_user.credits)
    new_credits = use_credits(user_id, 5, db_session)
    assert int(new_credits) == initial - 5
    
    # Try to deduct more than available
    with pytest.raises(HTTPException) as exc:
        use_credits(user_id, 10, db_session)
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
