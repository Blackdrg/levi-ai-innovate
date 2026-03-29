# pyright: reportMissingImports=false
import pytest  # type: ignore
import hmac
import hashlib
import os
from fastapi import HTTPException  # type: ignore
# from backend.main import verify_password, get_password_hash, create_access_token  # type: ignore
from backend.payments import verify_razorpay_signature, use_credits  # type: ignore

# ... existing code ...

@pytest.fixture
def test_user():
    return {
        "uid": "user_123", "email": "test@example.com",
        "username": "testuser", "tier": "free", "credits": 10
    }

from unittest.mock import patch, MagicMock

def test_credit_deduction(test_user):
    # Mock the Firestore call in payments.use_credits
    with patch('backend.payments.firestore_db') as mock_db:
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = test_user
        mock_db.collection().document().get.return_value = mock_doc
        
        # Call the actual function
        new_credits = use_credits(test_user["uid"], 5)
        
        assert new_credits == 5
        # Verify update was called
        mock_db.collection().document().update.assert_called_once_with({"credits": 5})

def test_credit_insufficient(test_user):
    with patch('backend.payments.firestore_db') as mock_db:
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"credits": 2, "tier": "free"}
        mock_db.collection().document().get.return_value = mock_doc
        
        with pytest.raises(HTTPException) as exc:
            use_credits(test_user["uid"], 5)
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

# ── Phase 18: Resiliency & Intelligence Tests ──────────────────

from backend.circuit_breaker import CircuitBreaker
from backend.agents import RouterAgent

def test_circuit_breaker_trips():
    """Verify that the circuit correctly opens after threshold failures."""
    # Using a longer recovery timeout for testing stability
    breaker = CircuitBreaker("TestBreaker", failure_threshold=2, recovery_timeout=10)
    
    def failing_func():
        raise Exception("Failure")
        
    # 1. First failure
    with pytest.raises(Exception):
        breaker.call(failing_func)
    assert breaker.state == "CLOSED"
    
    # 2. Threshold failure
    with pytest.raises(Exception):
        breaker.call(failing_func)
    assert breaker.state == "OPEN"
    
    # 3. Verify it stays open (should raise Exception without even calling the func)
    with pytest.raises(Exception) as exc:
        breaker.call(lambda: "should-not-hit")
    assert "is OPEN" in str(exc.value)

def test_router_agent_intent():
    """Verify intent classification routing logic."""
    agent = RouterAgent()
    
    # Mock the LLM call at the source
    with patch("backend.services.studio.router.generate_image_task.delay") as mock_task, \
         patch("backend.services.studio.router.use_credits") as mock_use_credits, \
         patch("backend.circuit_breaker.groq_breaker.call") as mock_call:
        # Create a mock response object that looks like Groq/OpenAI response
        mock_response = MagicMock()
        
        # 1. Test Chat Intent
        mock_response.choices[0].message.content = "{\"intent\": \"chat\", \"confidence\": 0.9}"
        mock_call.return_value = mock_response
        intent_info = agent.classify_intent("Hello there")
        assert intent_info["intent"] == "chat"
        
        # 2. Test Image Intent
        mock_response.choices[0].message.content = "{\"intent\": \"generate_image\", \"confidence\": 0.9, \"parameters\": {\"topic\": \"space\"}}"
        mock_call.return_value = mock_response
        intent_info = agent.classify_intent("Create an image about space")
        assert intent_info["intent"] == "generate_image"
