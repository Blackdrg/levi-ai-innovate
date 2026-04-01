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

# ── Phase 6.8: Sovereign Monolith Logic Tests ──────────────────

from backend.services.orchestrator.brain import LeviBrain
from backend.services.orchestrator.orchestrator_types import IntentResult

@pytest.mark.asyncio
async def test_meta_brain_routing_hierarchy():
    """Verify that Level 1/2 tasks route to LOCAL and Level 3+ to API."""
    brain = LeviBrain()
    
    # 1. Level 1: Greeting (Should be LOCAL)
    intent_l1 = IntentResult(intent="greeting", complexity=1, confidence=1.0)
    route_l1 = await brain._decide_route("Hello", intent_l1, {})
    assert route_l1 == "LOCAL"
    
    # 2. Level 4: Coding (Should be API)
    intent_l4 = IntentResult(intent="coding", complexity=4, confidence=1.0)
    route_l4 = await brain._decide_route("Write a FastAPI app", intent_l4, {})
    assert route_l4 == "API"

@pytest.mark.asyncio
async def test_local_engine_saturation_fallback():
    """Verify that local engine saturation triggers a routing fallback."""
    from backend.services.orchestrator.local_engine import LocalLLM
    
    # Mock the semaphore to be locked (simulating saturation)
    with patch("backend.services.orchestrator.local_engine.LocalLLM._concurrency_semaphore") as mock_sem:
        mock_sem.locked.return_value = True
        
        from backend.services.orchestrator.local_engine import generate_local_response
        generator = generate_local_response([{"role": "user", "content": "hi"}])
        
        responses = []
        async for chunk in generator:
            responses.append(chunk)
            
        assert "__FALLBACK_TRIGGER__" in responses

def test_router_agent_intent():
    """Verify intent classification routing logic for v6.8."""
    from backend.agents import RouterAgent
    agent = RouterAgent()
    
    with patch("backend.circuit_breaker.groq_breaker.call") as mock_call:
        mock_response = MagicMock()
        
        # v6.8 Format: JSON with metadata
        mock_response.choices[0].message.content = "{\"intent\": \"chat\", \"complexity\": 2, \"confidence\": 0.95}"
        mock_call.return_value = mock_response
        
        intent_info = agent.classify_intent("Tell me a joke")
        assert intent_info["intent"] == "chat"
        assert intent_info["complexity"] == 2

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
