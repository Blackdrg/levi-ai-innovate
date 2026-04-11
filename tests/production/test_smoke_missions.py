import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch, AsyncMock
from backend.core.orchestrator import Orchestrator
from backend.core.execution_state import MissionState, CentralExecutionState
from backend.core.orchestrator_types import ToolResult

@pytest.fixture
def orchestrator():
    orb = Orchestrator()
    return orb

@pytest.mark.asyncio
async def test_mission_confidence_gate_rejection(orchestrator):
    """Verify that missions with low confidence after refinement are rejected."""
    # Mock perception to return chat intent
    orchestrator.perception.perceive = AsyncMock(return_value={
        "intent": MagicMock(intent_type="complex", complexity_level=3, is_sensitive=False),
        "context": {}
    })
    
    # Mock planner
    orchestrator.planner.generate_decision = AsyncMock(return_value=MagicMock(mode=MagicMock(value="AUTONOMOUS"), enable_agents={}))
    orchestrator.planner.create_goal = AsyncMock(return_value=MagicMock(objective="Low confidence test"))
    orchestrator.planner.build_task_graph = AsyncMock(return_value=MagicMock(metadata={}, nodes=[]))
    orchestrator.planner.refine_plan = AsyncMock(return_value=MagicMock())
    
    # Mock reasoning to return LOW confidence (0.4)
    orchestrator.reasoning_core.evaluate_plan = AsyncMock(return_value={
        "graph": MagicMock(),
        "confidence": 0.4,
        "strategy": {"requires_refinement": True, "safe_mode": True},
        "critique": {"issues": ["Too shallow"], "warnings": []}
    })
    
    # Mock credits and other peripherals
    with patch('backend.services.billing_service.billing_service.deduct_credits', AsyncMock(return_value=True)), \
         patch('backend.db.redis.check_exact_match', return_value=None), \
         patch('backend.db.redis.check_semantic_match', return_value=None), \
         patch('backend.core.orchestrator.SovereignBroadcaster.publish'), \
         patch('backend.core.orchestrator.CognitiveTracer.start_trace'), \
         patch('backend.core.orchestrator.CognitiveTracer.add_step'), \
         patch('backend.core.orchestrator.CognitiveTracer.end_trace'):
        
        result = await orchestrator.handle_mission(
            user_input="This should fail due to low confidence",
            user_id="test_user",
            session_id="test_session"
        )
        
        assert result["status"] == "failed"
        assert "fidelity threshold" in result["response"]
        assert result["confidence"] == 0.4

@pytest.mark.asyncio
async def test_mission_timeout_enforcement(orchestrator):
    """Verify that missions that exceed MISSION_TIMEOUT are aborted."""
    orchestrator.MISSION_TIMEOUT = 1 # Set very low for test
    
    async def slow_perception(*args, **kwargs):
        await asyncio.sleep(2)
        return {"intent": MagicMock()}

    orchestrator.perception.perceive = slow_perception
    
    with patch('backend.core.orchestrator.CentralExecutionState.initialize'), \
         patch('backend.services.billing_service.billing_service.deduct_credits', AsyncMock(return_value=True)):
        
        result = await orchestrator.handle_mission(
            user_input="This should timeout",
            user_id="test_user",
            session_id="test_session"
        )
        
        assert result["status"] == "timeout"
        assert "timed out" in result["response"]

@pytest.mark.asyncio
async def test_graceful_drainage(orchestrator):
    """Verify that teardown_gracefully waits for active missions."""
    mission_id = "mission_drain_test"
    orchestrator.active_missions.add(mission_id)
    
    # Start a background task to simulate mission completion
    async def complete_mission_delayed():
        await asyncio.sleep(1)
        orchestrator.active_missions.discard(mission_id)
        
    asyncio.create_task(complete_mission_delayed())
    
    start_time = time.time()
    await orchestrator.teardown_gracefully(timeout=5)
    end_time = time.time()
    
    assert len(orchestrator.active_missions) == 0
    assert end_time - start_time >= 1 # Should have waited at least 1s

@pytest.mark.asyncio
async def test_force_abort(orchestrator):
    """Verify that force_abort transitions state and cancels executor."""
    mission_id = "mission_abort_test"
    orchestrator.active_missions.add(mission_id)
    
    with patch('backend.core.orchestrator.MissionControl.cancel') as mock_cancel, \
         patch('backend.core.orchestrator.CentralExecutionState.transition') as mock_transition:
        
        await orchestrator.force_abort(mission_id, "Testing abort")
        
        mock_transition.assert_called_with(MissionState.FAILED, term=pytest.any)
        mock_cancel.assert_called_with(mission_id)
        assert mission_id not in orchestrator.active_missions
