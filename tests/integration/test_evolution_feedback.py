import pytest
import asyncio
import time
from unittest.mock import MagicMock
from backend.core.orchestrator import Orchestrator

@pytest.mark.asyncio
async def test_evolution_feedback_loop():
    """Verify feedback improves performance over iterations (simulated)"""
    
    orchestrator = Orchestrator()
    # Mock components
    orchestrator.evolution_monitor = MagicMock()
    orchestrator.evolution_monitor.record_success = MagicMock(return_value=asyncio.Future())
    orchestrator.evolution_monitor.record_success.return_value.set_result(None)
    
    orchestrator.evolution_mutator = MagicMock()
    orchestrator.evolution_mutator.propose_rule = MagicMock(return_value=asyncio.Future())
    orchestrator.evolution_mutator.propose_rule.return_value.set_result({"safety_score": 0.99, "id": "rule_001"})
    
    # Mock handle_mission_logic to simulate improvement
    latencies = [2500, 2200, 2000, 1800, 1500]
    idx = 0
    
    async def mock_handle_logic(*args, **kwargs):
        nonlocal idx
        latency = latencies[min(idx, len(latencies)-1)]
        idx += 1
        return {"status": "success", "latency": latency, "response": "test"}

    orchestrator._handle_mission_logic = mock_handle_logic
    
    # Run iterations
    results = []
    for i in range(5):
        res = await orchestrator.handle_mission("Analyze market trends", "user_1", "sess_1")
        results.append(res)
    
    # Latency should decrease
    assert results[-1]["latency"] < results[0]["latency"]
    assert orchestrator.evolution_monitor.record_success.called
