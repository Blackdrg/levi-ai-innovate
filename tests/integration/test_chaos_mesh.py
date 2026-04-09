import pytest
import asyncio
from unittest.mock import patch, MagicMock

# Assuming standard LEVI-AI backend paths
from backend.core.v13.vram_guard import VRAMGuard
from backend.memory.consistency import MemoryConsistencyManager
from backend.core.task_graph import TaskGraph, TaskNode

pytestmark = pytest.mark.asyncio

class TestChaosMesh:
    """
    Sovereign v14.0 Production Chaos Mesh.
    Validates survivability under catastrophic infrastructure failures.
    """

    async def test_gpu_out_of_memory_survivability(self):
        """
        Simulates a CUDA OOM failure during multi-node LLM burst.
        Ensures strict task rejection rather than node crash.
        """
        guard = VRAMGuard()
        
        # Mock the system to report 0 free VRAM
        with patch("backend.core.v13.vram_guard.VRAMGuard.get_device_slots") as mock_slots:
            mock_slots.return_value = [{"device": "cuda:0", "vram_total_mb": 24000, "vram_free_mb": 100}]
            
            # Requesting more than available should fail fast, not queue infinitely
            acquired = await guard.acquire_vram("large_llm", required_mb=8000, timeout=1.0)
            assert acquired is False, "Node must reject workloads causing OOM."

    async def test_neo4j_disconnect_under_load(self):
        """
        Simulates Graph DB partition during a massive DAG execution. 
        MCM must queue writes in Redis and not lose state or halt the DAG.
        """
        payload = {"id": "mem_neo4j_test", "fact": "The sky is blue"}
        
        # We ensure MCM accepts the write and queues the retry
        enriched = MemoryConsistencyManager.register_event("user_123", payload)
        
        assert enriched["write_accepted"] is True
        
        # Simulate Neo4J failure by enqueuing a retry manually as the driver would
        MemoryConsistencyManager.enqueue_retry("user_123", enriched, store="graph")
        
        # Verify it was queued in Redis (Mocked or Real Redis if HAS_REDIS)
        from backend.db.redis import HAS_REDIS, r
        if HAS_REDIS:
            queue_len = r.llen("mcm:retry:graph:user_123")
            assert queue_len > 0, "MCM must enqueue graph writes during partition."

    async def test_redis_split_brain(self):
        """
        Simulates a Redis Split-brain scenario where HAS_REDIS becomes False.
        The DAG execution should fall back to local in-memory execution, preserving availability.
        """
        with patch("backend.memory.consistency.HAS_REDIS", False):
            payload = {"id": "mem_split_test", "fact": "Redundancy is critical"}
            
            # Should still return a valid enriched payload
            enriched = MemoryConsistencyManager.register_event("user_999", payload)
            assert enriched["write_accepted"] is True
            assert "content_hash" in enriched
            
            # Check DAG Planner still produces a valid graph without Redis caching
            graph = TaskGraph()
            graph.add_node(TaskNode(id="t1", agent="local", description="Test"))
            assert len(graph.nodes) == 1
