import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from backend.core.v8.brain import LeviBrainV8
from backend.core.orchestrator_types import IntentResult, ToolResult

@pytest.mark.asyncio
async def test_v8_cognitive_flow():
    # 1. Setup Brain
    brain = LeviBrainV8()
    
    # Mock dependencies
    brain.memory.get_combined_context = AsyncMock(return_value={"history": [], "user_tier": "free"})
    brain.memory.store_memory = AsyncMock()
    
    # Mock Intent Detection
    from backend.core.planner import detect_intent
    import backend.core.planner
    backend.core.planner.detect_intent = AsyncMock(return_value=IntentResult(
        intent_type="chat", complexity_level=1, confidence_score=0.9
    ))
    
    # Mock Tool Registry (for agents)
    from backend.core.tool_registry import call_tool
    import backend.core.tool_registry
    backend.core.tool_registry.call_tool = AsyncMock(side_effect=[
        # chat_agent call
        {"success": True, "message": "Hello from V8!", "data": {}},
        # critic_agent call
        {"success": True, "message": "Good", "data": {"quality_score": 0.95, "issues": []}}
    ])

    # 2. Run Brain
    result = await brain.run("Hello LEVI", "user_123", "session_456")
    
    # 3. Assertions
    assert "response" in result
    assert result["response"] == "Hello from V8!"
    assert result["goal"]["objective"] == "Synthesize coherent response: Hello LEVI"
    assert len(result["results"]) > 0
    assert result["results"][0]["message"] == "Hello from V8!"
    
    print("\n[V8 Test] Cognitive flow verified successfully!")

if __name__ == "__main__":
    asyncio.run(test_v8_cognitive_flow())
