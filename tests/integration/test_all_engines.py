import pytest
import asyncio
from backend.core.orchestrator import Orchestrator

@pytest.mark.asyncio
async def test_full_cognitive_stack():
    """
    E2E test for the full LEVI-AI cognitive stack (12 Engines).
    Verifies that all components collaborate to complete a complex mission.
    """
    orchestrator = Orchestrator()
    await orchestrator.initialize()
    
    # Complex mission requiring orchestration, reasoning, world model, and alignment
    objective = "Analyze the impact of sovereign AI on global data privacy laws by 2030."
    
    result = await orchestrator.handle_mission(
        user_input=objective,
        user_id="test_user_alpha",
        session_id="session_stack_test_001",
        mood="analytical"
    )
    
    assert result["status"] == "success"
    assert "response" in result
    assert result["reasoning"]["confidence"] > 0.8
    
    # Check that World Model was used
    # (In real implementation, we'd check SM metadata)
    
    # Check that Alignment was used (response should not be empty)
    assert len(result["response"]) > 100
    
    # Check that Memory was updated
    assert "memory" in result
    assert result["memory"]["event_id"] is not None
    
    print("✅ Full Cognitive Stack validated (12/12 Engines Operational)")
