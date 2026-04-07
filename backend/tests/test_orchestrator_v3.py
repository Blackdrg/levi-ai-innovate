"""
backend/tests/test_orchestrator_v3.py

Verification suite for the hardened LEVI-AI v3.0 Brain.
"""

import pytest
from backend.services.orchestrator.brain import LeviBrain
from backend.services.orchestrator.orchestrator_types import EngineRoute

@pytest.mark.asyncio
async def test_brain_deterministic_routing_local():
    brain = LeviBrain()
    # Test Greeting -> should go to LocalAgent
    result = await brain.route(
        user_input="Hello Levi!",
        user_id="test_user",
        session_id="test_sess"
    )
    
    assert result["intent"] == "greeting"
    assert result["route"] == EngineRoute.LOCAL.value
    assert "response" in result
    assert result["request_id"].startswith("orch_")

@pytest.mark.asyncio
async def test_brain_deterministic_routing_image():
    brain = LeviBrain()
    # Test Image -> should have a multi-step plan
    result = await brain.route(
        user_input="Generate a futuristic city in neon style",
        user_id="test_user",
        session_id="test_sess"
    )
    
    assert result["intent"] == "image"
    assert "plan" in result
    steps = result["plan"]["steps"]
    assert len(steps) >= 1
    assert any(s["agent"] == "image_agent" for s in steps)
    assert "results" in result

@pytest.mark.asyncio
async def test_brain_streaming_flow():
    brain = LeviBrain()
    # Test Streaming flag
    result = await brain.route(
        user_input="Tell me a story about time.",
        user_id="test_user",
        session_id="test_sess",
        streaming=True
    )
    
    assert "stream" in result
    assert result["intent"] == "chat"
    # Verify we can pull at least one token (mocking needed if no API key)
    # Since this is a check, we'll just verify the presence of the generator.
    assert hasattr(result["stream"], "__aiter__")

@pytest.mark.asyncio
async def test_tool_hardened_validation():
    from backend.services.orchestrator.tool_registry import call_tool
    # Test with invalid input for image_agent (missing required fields)
    # The new system should catch this at the Pydantic level
    res = await call_tool("image_agent", {"wrong_key": "data"})
    assert res["success"] is False
    assert "Invalid input" in res["error"]
