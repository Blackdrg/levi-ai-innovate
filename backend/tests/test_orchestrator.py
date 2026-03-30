import pytest
import asyncio
from backend.services.orchestrator import run_orchestrator
from backend.services.orchestrator.planner import detect_intent
from backend.services.orchestrator.engine import decide_engine
from backend.services.orchestrator.orchestrator_types import IntentResult

@pytest.mark.asyncio
async def test_detect_intent_image():
    result = await detect_intent("Can you draw a futuristic city?")
    assert result.intent == "image"
    assert result.complexity >= 5

@pytest.mark.asyncio
async def test_detect_intent_code():
    result = await detect_intent("Write a python script to sort a list")
    assert result.intent == "code"

@pytest.mark.asyncio
async def test_decide_engine_free_tier():
    intent = IntentResult(intent="chat", confidence=1.0, complexity=2)
    context = {"user_tier": "free"}
    config = await decide_engine(intent, context)
    assert config["model"] == "llama-3.1-8b-instant"

@pytest.mark.asyncio
async def test_decide_engine_pro_tier():
    intent = IntentResult(intent="chat", confidence=1.0, complexity=2)
    context = {"user_tier": "pro"}
    config = await decide_engine(intent, context)
    assert config["model"] == "llama-3.1-70b-versatile"

@pytest.mark.asyncio
async def test_orchestrator_flow():
    # This might require Mocks for LLM APIs if run in a pure CI environment
    # For now, we test the logic flow
    response = await run_orchestrator(
        user_input="Hello LEVI, who are you?",
        session_id="test_session",
        user_id="test_user",
        user_tier="free"
    )
    assert isinstance(response, str)
    assert len(response) > 0
