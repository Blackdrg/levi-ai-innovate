"""
backend/tests/test_orchestrator.py

Legacy CI test suite — updated for v2.0 Brain API.

Key API changes from v1.x:
  - decide_engine()  → route_request() (sync, returns (EngineRoute, config))
  - run_orchestrator() now returns Dict, not str
"""
import pytest
from unittest.mock import patch, AsyncMock

from backend.services.orchestrator import run_orchestrator
from backend.services.orchestrator.planner import detect_intent, check_rules
from backend.services.orchestrator.engine import route_request
from backend.services.orchestrator.orchestrator_types import IntentResult, EngineRoute


# ---------------------------------------------------------------------------
# Intent Detection
# ---------------------------------------------------------------------------

def test_detect_intent_image_via_rules():
    """Regex rules should instantly classify image requests."""
    result = check_rules("Can you draw a futuristic city?")
    assert result is not None
    assert result.intent == "image"


def test_detect_intent_code_via_rules():
    """Regex rules should instantly classify code requests."""
    result = check_rules("Write a python script to sort a list")
    assert result is not None
    assert result.intent == "code"


def test_detect_intent_greeting_via_rules():
    """Regex rules should instantly classify greetings."""
    result = check_rules("hello")
    assert result is not None
    assert result.intent == "greeting"


# ---------------------------------------------------------------------------
# Decision Engine (route_request — v2.0 name)
# ---------------------------------------------------------------------------

def test_route_request_free_tier_chat():
    """Free tier chat → API route with lightweight model."""
    intent = IntentResult(intent="chat", confidence=1.0, complexity=5)
    context = {"user_tier": "free"}
    route, config = route_request(intent, context)
    assert route == EngineRoute.API
    assert config["model"] == "llama-3.1-8b-instant"


def test_route_request_pro_tier_chat():
    """Pro tier → API route with power model."""
    intent = IntentResult(intent="chat", confidence=1.0, complexity=5)
    context = {"user_tier": "pro"}
    route, config = route_request(intent, context)
    assert route == EngineRoute.API
    assert config["model"] == "llama-3.1-70b-versatile"


def test_route_request_greeting_is_local():
    """Greetings must always route LOCAL (zero API cost)."""
    intent = IntentResult(intent="greeting", confidence=0.99, complexity=1)
    context = {"user_tier": "free"}
    route, config = route_request(intent, context)
    assert route == EngineRoute.LOCAL
    assert config["model"] == "none"


def test_route_request_image_is_tool():
    """Image intent must route TOOL."""
    intent = IntentResult(intent="image", confidence=0.9, complexity=4)
    context = {"user_tier": "free"}
    route, config = route_request(intent, context)
    assert route == EngineRoute.TOOL


# ---------------------------------------------------------------------------
# Full Orchestrator Pipeline
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrator_returns_dict():
    """
    run_orchestrator must return a dict with 'response' key.
    Mocks all external services to run fully offline.
    """
    mock_db = AsyncMock()
    mock_db.collection.return_value.where.return_value \
        .order_by.return_value.limit.return_value.stream.return_value = iter([])
    mock_db.collection.return_value.where.return_value \
        .limit.return_value.stream.return_value = iter([])

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True

    with (
        patch("backend.db.redis_client.get_conversation",   return_value=[]),
        patch("backend.db.redis_client.save_conversation",  return_value=None),
        patch("backend.db.redis_client.HAS_REDIS",          True),
        patch("backend.db.redis_client.r",                  mock_redis),
        patch("backend.db.firestore_db.db",                 mock_db),
        patch("backend.services.orchestrator.engine.check_allowance", return_value=True),
        patch("backend.payments.use_credits",            return_value=None),
        patch("backend.embeddings.embed_text",           return_value=[0.1] * 384),
        patch(
            "backend.generation._async_call_llm_api",
            new_callable=AsyncMock,
            return_value='{"intent": "chat", "complexity": 3, "confidence": 0.7}',
        ),
    ):
        result = await run_orchestrator(
            user_input="Hello LEVI, who are you?",
            session_id="test_session",
            user_id="test_user",
            user_tier="free",
        )

    assert isinstance(result, dict)
    assert "response" in result
    assert isinstance(result["response"], str)
    assert len(result["response"]) > 0


@pytest.mark.asyncio
async def test_orchestrator_greeting_uses_local_route():
    """
    Greeting input must be served by LOCAL engine (no Groq call).
    """
    mock_db = AsyncMock()
    mock_db.collection.return_value.where.return_value \
        .order_by.return_value.limit.return_value.stream.return_value = iter([])
    mock_db.collection.return_value.where.return_value \
        .limit.return_value.stream.return_value = iter([])
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    with (
        patch("backend.db.redis_client.get_conversation",   return_value=[]),
        patch("backend.db.redis_client.save_conversation",  return_value=None),
        patch("backend.db.redis_client.HAS_REDIS",          True),
        patch("backend.db.redis_client.r",                  mock_redis),
        patch("backend.db.firestore_db.db",                 mock_db),
        patch("backend.services.orchestrator.engine.check_allowance", return_value=True),
        patch("backend.payments.use_credits",            return_value=None),
        patch("backend.embeddings.embed_text",           return_value=[0.1] * 384),
        patch(
            "backend.generation._async_call_llm_api",
            new_callable=AsyncMock,
            return_value='{"intent": "chat", "complexity": 1, "confidence": 0.9}',
        ),
    ):
        result = await run_orchestrator(
            user_input="hello",
            session_id="test_greet",
            user_id="test_user",
            user_tier="free",
        )

    assert result["route"] == "local"
    assert len(result["response"]) > 4
