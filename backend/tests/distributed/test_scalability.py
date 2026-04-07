import asyncio
import json
import logging
import pytest
from backend.core.v13.vram_guard import VRAMGuard
from backend.core.dcn.resource_manager import ResourceManager
from backend.core.executor.streams import StreamManager
from backend.db.redis import r_async, HAS_REDIS_ASYNC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_vram_guard():
    guard = VRAMGuard()
    slots = await guard.get_device_slots()
    assert len(slots) > 0
    assert slots[0]["id"].startswith("gpu-")
    logger.info(f"VRAMGuard Test Passed. Slots: {slots}")

@pytest.mark.asyncio
async def test_resource_registry_and_manager():
    if not HAS_REDIS_ASYNC: pytest.skip("Redis not available")
    
    # Mock a node heartbeat
    node_id = "test-node-1"
    node_data = {
        "node_id": node_id,
        "role": "worker",
        "weight": 4,
        "device_slots": [
            {"id": "gpu-0", "vram_free_mb": 32000, "vram_total_mb": 32000}
        ],
        "cpu_percent": 10
    }
    
    await r_async.hset("dcn:swarm:nodes", node_id, json.dumps(node_data))
    
    mgr = ResourceManager()
    best_node = await mgr.find_optimal_node("L3")
    assert best_node == node_id
    
    stats = await mgr.get_cluster_stats()
    assert stats["node_count"] >= 1
    logger.info(f"ResourceManager Test Passed. Stats: {stats}")

@pytest.mark.asyncio
async def test_stream_lifecycle():
    if not HAS_REDIS_ASYNC: pytest.skip("Redis not available")
    
    streams = StreamManager()
    await streams.setup_groups()
    
    task = {"mission_id": "test_m", "node_id": "n1", "model_tier": "L2"}
    msg_id = await streams.enqueue_task(task, priority="high")
    assert msg_id is not None
    
    pulled = await streams.pull_tasks("test_consumer", count=1)
    assert len(pulled) == 1
    assert pulled[0][0] == msg_id
    assert pulled[0][1]["mission_id"] == "test_m"
    
    await streams.acknowledge_task(msg_id)
    # Verify no more pending
    pending = await r_async.xpending(streams.stream_name, streams.group_name)
    assert pending["count"] == 0
    logger.info("StreamManager Lifecycle Test Passed.")

if __name__ == "__main__":
    asyncio.run(test_vram_guard())
    asyncio.run(test_resource_registry_and_manager())
    asyncio.run(test_stream_lifecycle())
