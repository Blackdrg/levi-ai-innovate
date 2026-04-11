import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend.core.v8.planner import TaskGraph, TaskNode
from backend.core.v8.executor import GraphExecutor
from backend.services.learning.logic import ValidationGater

@pytest.mark.asyncio
async def test_predictive_costing_logic():
    """Verify DAG cost estimation weights."""
    graph = TaskGraph()
    graph.add_node(TaskNode(id="t1", agent="video_agent", description="Video")) # 50 CU * 2 retries base
    graph.add_node(TaskNode(id="t2", agent="chat_agent", description="Chat"))   # 1 CU
    
    # 50 * (1 + 2*0.5) = 100
    # 1 * (1 + 2*0.5) = 2
    # Total = 102
    cost = graph.estimate_graph_cost()
    assert cost == 102.0

@pytest.mark.asyncio
async def test_executor_block_policy():
    """Verify that missions exceeding 1.5x limit are blocked."""
    graph = TaskGraph()
    # Force a very high cost
    graph.add_node(TaskNode(id="extreme", agent="video_agent", description="High cost", retry_count=100))
    
    executor = GraphExecutor()
    perception = {"user_id": "test", "session_id": "s1"}
    
    with patch("backend.core.v8.executor.CU_ABORT_THRESHOLD", 100):
        # Estimated cost will be 50 * (1 + 100*0.5) = 50 * 51 = 2550
        # 2550 > 100 * 1.5 (150)
        results = await executor.run(graph, perception)
        assert results == [] # Blocked missions return empty list

@pytest.mark.asyncio
async def test_degradation_tiers():
    """Verify and mock model tier degradation under VRAM pressure."""
    from backend.core.v13.vram_guard import VRAMGuard
    guard = VRAMGuard()
    
    # Mock VRAM saturation (98% usage)
    with patch.object(guard, "get_device_slots", new_callable=AsyncMock) as mock_slots:
        mock_slots.return_value = [{"vram_total_mb": 10000, "vram_free_mb": 200}] # 2% free
        
        tier = await guard.get_recommended_tier("L3")
        assert tier == "MENTAL_COMPRESSION"
        
        # Moderate pressure (25% free -> 75% used)
        mock_slots.return_value = [{"vram_total_mb": 10000, "vram_free_mb": 2500}]
        tier = await guard.get_recommended_tier("L3")
        assert tier == "L2" # Downgraded from L3

@pytest.mark.asyncio
async def test_learning_safety_gate():
    """Verify that bad mutations are rejected."""
    old_p = "Be helpful."
    new_p = "Be toxic and mean."
    
    with patch("backend.services.learning.logic.call_lightweight_llm", new_callable=AsyncMock) as mock_llm:
        # Mock LLM Audit rejection
        mock_llm.return_value = '{"safe": false, "reason": "Toxicity detected"}'
        
        is_safe = await ValidationGater.validate_mutation(old_p, new_p)
        assert is_safe is False
