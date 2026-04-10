import asyncio
import pytest
from backend.core.executor.compensation_coordinator import CompensationCoordinator

@pytest.mark.asyncio
async def test_compensation_stack_integrity():
    """Verify that steps are reversed in LIFO order with correct params."""
    coordinator = CompensationCoordinator(mission_id="chaos_test_001")
    
    execution_order = []
    
    async def reverse_action(step_id, val):
        execution_order.append((step_id, val))
    
    # Register 3 steps
    coordinator.register_step("node_1", "write_a", reverse_action, {"step_id": 1, "val": "A"})
    coordinator.register_step("node_2", "write_b", reverse_action, {"step_id": 2, "val": "B"})
    coordinator.register_step("node_3", "write_c", reverse_action, {"step_id": 3, "val": "C"})
    
    # Trigger Compensation
    result = await coordinator.compensate()
    
    assert result["status"] == "completed"
    assert len(result["steps"]) == 3
    
    # Verify LIFO (Reverse) Order: 3 -> 2 -> 1
    assert execution_order == [
        (3, "C"),
        (2, "B"),
        (1, "A")
    ]

@pytest.mark.asyncio
async def test_compensation_partial_failure():
    """Verify that compensation continues even if one reversal step fails (Chaos)."""
    coordinator = CompensationCoordinator(mission_id="chaos_test_002")
    
    success_tracker = []
    
    async def failing_action():
        raise RuntimeError("Chaos Failure")
        
    async def successful_action(name):
        success_tracker.append(name)

    coordinator.register_step("good_1", "act", successful_action, {"name": "first"})
    coordinator.register_step("bad_2", "act", failing_action, {})
    coordinator.register_step("good_3", "act", successful_action, {"name": "third"})
    
    result = await coordinator.compensate()
    
    # Order: 3 (good) -> 2 (bad) -> 1 (good)
    assert len(success_tracker) == 2
    assert "third" in success_tracker
    assert "first" in success_tracker
    
    # Check results for failure tracking
    failed_steps = [s for s in result["steps"] if s["status"] == "failed"]
    assert len(failed_steps) == 1
    assert failed_steps[0]["node_id"] == "bad_2"
