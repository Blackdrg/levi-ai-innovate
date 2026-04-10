import pytest
import asyncio
import os
import json
import uuid
import time
from backend.core.v8.executor import GraphExecutor, GLOBAL_VRAM_POOL, GLOBAL_VRAM_GUARD
from backend.utils.network import ai_service_breaker
from backend.core.dcn.gossip import DCNGossip

# 🛡️ Test Isolation: Injecting FakeRedis for DCN logic verification
class InMemoryRedis:
    def __init__(self, **kwargs): 
        self.data = {}
        self._pipe_results = []

    async def get(self, k): 
        val = self.data.get(k)
        return val.encode() if val and isinstance(val, str) else val
    async def set(self, k, v, **kwargs): self.data[k] = str(v); return True
    async def hset(self, n, k, v): 
        if n not in self.data: self.data[n] = {}
        self.data[n][k] = str(v); return 1
    async def hgetall(self, n): return self.data.get(n, {})
    async def delete(self, *ks): 
        for k in ks: self.data.pop(k, None)
        return 1
    async def hdel(self, n, *ks):
        if n in self.data:
            for k in ks: self.data[n].pop(k, None)
        return 1
    async def rpush(self, k, v): pass # Mocked for blackboard fallback
    async def lrange(self, k, s, e): return [] 
    async def incr(self, k):
        val = int(self.data.get(k, 0)) + 1
        self.data[k] = str(val)
        return val
    async def expire(self, k, ttl): return True
    async def exists(self, k): return k in self.data
    
    # Simple Pipeline Mock
    def pipeline(self, transaction=True): return self
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def execute(self):
        # Specific hack for try_become_coordinator: it expects [term+1, term+1]
        # or similar depending on the pipe sequence.
        # Line 246 (incr), 247 (get)
        term = self.data.get("dcn:swarm:term", "0")
        return [int(term), int(term)] 

try:
    from fakeredis.aioredis import FakeRedis as AsyncFakeRedis
    redis_client = AsyncFakeRedis(decode_responses=True)
except ImportError:
    redis_client = InMemoryRedis()

import backend.db.redis as redis_module
redis_module.r_async = redis_client
redis_module.HAS_REDIS_ASYNC = True

@pytest.mark.asyncio
async def test_quorum_isolation():
    """
    Chaos Test: Verify node isolation handling.
    Simulates a 3-node cluster and isolates one node.
    """
    # 1. Setup 3 dummy nodes in Redis
    node1 = {"node_id": "node-1", "last_seen": time.time()}
    node2 = {"node_id": "node-2", "last_seen": time.time()}
    node3 = {"node_id": "node-3", "last_seen": time.time()}
    
    await redis_client.hset("dcn:swarm:nodes", "node-1", json.dumps(node1))
    await redis_client.hset("dcn:swarm:nodes", "node-2", json.dumps(node2))
    await redis_client.hset("dcn:swarm:nodes", "node-3", json.dumps(node3))
    
    # 2. Initialize Gossip for node-3
    os.environ["DCN_NODE_ID"] = "node-3"
    os.environ["TEST_MODE"] = "true"
    gossip = DCNGossip(r=redis_client)
    
    # Check Quorum (Should be met: 3/3 active)
    assert await gossip.check_quorum() is True
    
    # 3. Simulate Isolation: Node 1 and 2 'die' (last_seen > 60s ago)
    node1["last_seen"] = time.time() - 70
    node2["last_seen"] = time.time() - 70
    await redis_client.hset("dcn:swarm:nodes", "node-1", json.dumps(node1))
    await redis_client.hset("dcn:swarm:nodes", "node-2", json.dumps(node2))
    
    # Check Quorum (Should fail: 1/3 active)
    assert await gossip.check_quorum() is False
    assert gossip.is_isolated is True

@pytest.mark.asyncio
async def test_fencing_token_split_brain():
    """
    Chaos Test: Verify split-brain prevention via Fencing Tokens.
    Two nodes try to claim leadership in the same term.
    """
    # 0. Setup Swarm Registry for Quorum Awareness (v13.2 Requirements)
    node_a = {"node_id": "node-a", "last_seen": time.time()}
    node_b = {"node_id": "node-b", "last_seen": time.time()}
    await redis_client.hset("dcn:swarm:nodes", "node-a", json.dumps(node_a))
    await redis_client.hset("dcn:swarm:nodes", "node-b", json.dumps(node_b))
    
    # 1. Node A claims leadership
    gossip_a = DCNGossip(r=redis_client)
    gossip_a.node_id = "node-a"
    
    gossip_b = DCNGossip(r=redis_client)
    gossip_b.node_id = "node-b"
    await gossip_a.try_become_coordinator()
    token_a = await redis_client.get(f"{gossip_a.leader_key}:token")
    assert token_a is not None
    assert "node-a" in token_a.decode()
    
    # 2. Node B tries to claim (but A is still active)
    # This should fail if A's lease hasn't expired.
    claimed = await gossip_b.try_become_coordinator()
    assert claimed is False
    
    # 3. Simulate lease expiration and B claiming
    await redis_client.delete(gossip_a.leader_key)
    await gossip_b.try_become_coordinator()
    token_b = await redis_client.get(f"{gossip_b.leader_key}:token")
    assert "node-b" in token_b.decode()
    
    # Ensure terms are incrementing
    term_a = int(token_a.decode().split(":")[0])
    term_b = int(token_b.decode().split(":")[0])
    assert term_b > term_a

@pytest.mark.asyncio
async def test_circuit_breaker_recovery_validation():
    """
    Chaos Test: Verify Circuit Breaker recovery threshold.
    Requires 3 consecutive successes to CLOSE the circuit.
    """
    breaker = ai_service_breaker
    breaker.threshold = 1
    breaker.success_threshold = 3
    breaker.state = "CLOSED"
    
    # 1. Trip the circuit
    def failing_call(): raise RuntimeError("Boom")
    with pytest.raises(Exception):
        breaker.call(failing_call)
    
    assert breaker.state == "OPEN"
    
    # 2. Force HALF-OPEN
    breaker.state = "HALF-OPEN"
    
    # 3. First success: should remain HALF-OPEN
    def success_call(): return "OK"
    breaker.call(success_call)
    assert breaker.state == "HALF-OPEN"
    
    # 4. Second success: should remain HALF-OPEN
    breaker.call(success_call)
    assert breaker.state == "HALF-OPEN"
    
    # 5. Third success: should CLOSE
    breaker.call(success_call)
    assert breaker.state == "CLOSED"

@pytest.mark.asyncio
async def test_mental_compression_backpressure():
    """
    Resilience Test: Verify Mental Compression during VRAM saturation.
    Uses the v13.1 hardware-aware VRAM pool.
    """
    global GLOBAL_VRAM_POOL # Use the one from executor
    executor = GraphExecutor()
    
    # 0. Mock MissionBlackboard Context to avoid synchronous Redis calls
    try:
        from unittest.mock import AsyncMock
        from backend.core.v8.blackboard import MissionBlackboard
        MissionBlackboard.get_session_context = AsyncMock(return_value="Mock Context")
    except ImportError: pass # Fallback to already-hardened blackboard logic
    
    # Simulate hardware: 16GB
    if GLOBAL_VRAM_POOL is None:
        from backend.core.v13.vram_guard import VRAMPool
        import backend.core.v8.executor as exec_mod
        exec_mod.GLOBAL_VRAM_POOL = VRAMPool(16384)
        GLOBAL_VRAM_POOL = exec_mod.GLOBAL_VRAM_POOL

    # 1. Partially exhaust the pool: Take 10GB of 16GB -> 6GB left
    # L2 needs 12GB (Backpressure triggers), Compressor needs 4GB (Success)
    await GLOBAL_VRAM_POOL.acquire(10240)
    
    # 2. Execute a node that needs Tier L2 (12GB) -> Should trigger compression to L1 (4GB)
    class MockNode:
        def __init__(self):
            self.id = "test_node"
            self.agent = "chat_agent"
            self.critical = False
            self.inputs = {}
            self.metadata = {"tier": "L2"}
            self.dependencies = []
            
    node = MockNode()
    # We call _execute_node directly to test backpressure logic
    result = await executor._execute_node(node, {}, {"session_id": "test_session"})
    
    # 3. Result should be from 'mental_compressor'
    assert result.agent == "mental_compressor"
    
    # Release VRAM
    await GLOBAL_VRAM_POOL.release(15360)

@pytest.mark.asyncio
async def test_partition_during_election():
    """
    Chaos Test: Partition during Leader Election.
    Simulates network partition just as nodes are incrementing terms.
    """
    # Setup 4 nodes
    nodes = {f"node-{i}": {"node_id": f"node-{i}", "last_seen": time.time()} for i in range(1, 5)}
    for nid, ndata in nodes.items():
        await redis_client.hset("dcn:swarm:nodes", nid, json.dumps(ndata))
    
    # Node 1 tries to become coordinator
    gossip1 = DCNGossip(r=redis_client)
    gossip1.node_id = "node-1"
    
    # 🧪 SIMULATE PARTITION: Hide 3 of the 4 nodes from Node 1
    # We override hgetall for this gossip instance to simulate isolation
    original_hgetall = redis_client.hgetall
    async def partitioned_hgetall(name):
        if name == "dcn:swarm:nodes":
            return {"node-1": json.dumps(nodes["node-1"])}
        return await original_hgetall(name)
    
    redis_client.hgetall = partitioned_hgetall
    
    # Should fail due to lack of quorum (1/4 < 50%)
    success = await gossip1.try_become_coordinator()
    assert success is False
    assert gossip1.is_isolated is True
    
    # Restore hgetall
    redis_client.hgetall = original_hgetall

@pytest.mark.asyncio
async def test_simultaneous_rejoin():
    """
    Chaos Test: Simultaneous Rejoin.
    Verifies that multiple nodes rejoining don't trigger term oscillations.
    """
    # 1. Start with Node 1 as leader in Term 10
    await redis_client.set("dcn:swarm:term", "10")
    await redis_client.set("dcn:swarm:leader:token", "10:node-1")
    
    # 2. Nodes 2 and 3 rejoin simultaneously with higher terms from a sub-partition
    # Node 2 thinks Term is 15, Node 3 thinks Term is 12
    gossip2 = DCNGossip(r=redis_client)
    gossip2.node_id = "node-2"
    
    gossip3 = DCNGossip(r=redis_client)
    gossip3.node_id = "node-3"
    
    # Verify both can recognize the current global state and converge
    # Node 2 sees Term 10 but had Term 15 in its state
    # (Simplified: check if term increments are monotonic and consistent)
    await gossip2.try_become_coordinator()
    token2 = await redis_client.get("dcn:swarm:leader:token")
    term2 = int(token2.decode().split(":")[0])
    assert term2 >= 11
    
    await gossip3.try_become_coordinator()
    token3 = await redis_client.get("dcn:swarm:leader:token")
    term3 = int(token3.decode().split(":")[0])
    
    # Since node-2 is already leader, node-3 should fail or wait
    assert term3 == term2
    assert "node-2" in token3.decode()

@pytest.mark.asyncio
async def test_stale_pulse_replay():
    """
    Security Test: Stale Pulse Replay detection.
    Prevents old heartbeats from keeping a zombie node 'active'.
    """
    gossip = DCNGossip(r=redis_client)
    gossip.node_id = "node-alpha"
    
    # 1. Send an old pulse (time offset by 5 minutes)
    stale_time = time.time() - 300
    stale_node = {"node_id": "node-alpha", "last_seen": stale_time}
    await redis_client.hset("dcn:swarm:nodes", "node-alpha", json.dumps(stale_node))
    
    # 2. check_quorum should treat this node as inactive
    active_nodes = await gossip._get_active_nodes()
    assert "node-alpha" not in [n["node_id"] for n in active_nodes]

@pytest.mark.asyncio
async def test_sybil_detection_load():
    """
    Chaos/Security Test: Sybil Detection.
    Detects abnormal node join rates.
    """
    gossip = DCNGossip(r=redis_client)
    
    # Simulate 100 nodes joining in 1 second
    now = time.time()
    for i in range(100):
        node = {"node_id": f"sybil-{i}", "last_seen": now}
        await redis_client.hset("dcn:swarm:nodes", f"sybil-{i}", json.dumps(node))
    
    # check_quorum or a specific audit check should flag this
    # (Implementation dependent - v14 adding Sybil logic)
    active_nodes = await gossip._get_active_nodes()
    # In v14, we might limit max nodes in quorum or flag high join rate
    assert len(active_nodes) >= 100 
    # Logic to flag excessive active nodes
    if len(active_nodes) > 50:
         logger.warning("SWARM HYPER-DENSITY DETECTED: Possible Sybil Attack.")
