import pytest
import asyncio
from unittest.mock import MagicMock, patch
from backend.services.orchestrator.brain import LeviBrain
from backend.services.orchestrator.orchestrator_types import IntentResult, EngineRoute

@pytest.mark.asyncio
async def test_v6_sovereign_routing_l0():
    """
    Verifies that Level 0 (Greeting) intent is routed to the LOCAL engine 
    and skips expensive reasoning.
    """
    brain = LeviBrain()
    
    # Mock Intent Detection
    mock_intent = IntentResult(
        intent="greeting",
        complexity=0,
        confidence=0.99,
        intent_type="greeting",
        complexity_level=0,
        confidence_score=0.99,
        estimated_cost_weight=0.0
    )
    
    with patch("backend.services.orchestrator.brain.detect_intent", return_value=mock_intent), \
         patch("backend.services.orchestrator.brain.is_locally_handleable", return_value=True), \
         patch("backend.services.orchestrator.brain.MemoryManager.get_combined_context", return_value={"history": []}), \
         patch("backend.services.orchestrator.brain.call_tool", return_value={"message": "Hello from Local Agent", "success": True}):
        
        result = await brain.route("Hi LEVI", "user_123", "sess_123")
        
        assert result["route"] == EngineRoute.LOCAL.value
        assert "Hello from Local Agent" in result["response"]
        print("\n✅ L0 Sovereign Routing Verified: Success")

@pytest.mark.asyncio
async def test_v6_metabrain_local_decomposition():
    """
    Verifies that for Complexity < 3, the Meta-Brain uses the LOCAL engine 
    for goal decomposition instead of hitting external APIs.
    """
    from backend.services.orchestrator.meta_planner import decompose_goal, GoalStrategy, SubGoal
    
    mock_intent = IntentResult(
        intent="simple_task",
        complexity=2,
        intent_type="simple_task",
        complexity_level=2,
        confidence_score=0.9
    )
    
    mock_strategy = GoalStrategy(
        overall_strategy="Local decomposition test",
        subgoals=[SubGoal(description="Test goal", target_agent="chat_agent")],
        recommended_model="llama-3.1-8b-instant"
    )
    
    with patch("backend.services.orchestrator.meta_planner.is_locally_handleable", return_value=True), \
         patch("backend.services.orchestrator.meta_planner.handle_local_sync", return_value=mock_strategy.json()), \
         patch("backend.services.orchestrator.meta_planner._async_call_llm_api") as mock_api:
        
        strategy = await decompose_goal("Make a list of 3 colors", mock_intent, {})
        
        assert strategy.overall_strategy == "Local decomposition test"
        mock_api.assert_not_called() # Should NEVER hit the API for L2 tasks
        print("✅ Meta-Brain Local Decomposition Verified: Success")

if __name__ == "__main__":
    asyncio.run(test_v6_sovereign_routing_l0())
    asyncio.run(test_v6_metabrain_local_decomposition())
