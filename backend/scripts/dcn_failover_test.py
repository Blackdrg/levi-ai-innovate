import asyncio
import os
import logging
from backend.core.dcn.gossip import DCNGossip

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DCNFailoverTest")

async def simulate_swarm():
    """
    Sovereign v13.1 DCN Certification: Failover Drill.
    Simulates a 2nd Node competing for sticky leadership.
    """
    # Node 1: Current Coordinator
    node1 = DCNGossip()
    node1.node_id = "node-alpha"
    node1.lease_ttl = 5 # Short TTL for test speed
    
    # Node 2: Standby Worker
    node2 = DCNGossip()
    node2.node_id = "node-beta"
    node2.lease_ttl = 5
    
    logger.info("📡 [Drill] Initiating Swarm Failover Simulation...")
    
    # 1. Node 1 takes leadership
    await node1.try_become_coordinator()
    assert node1.is_coordinator is True
    
    # 2. Node 2 tries to take leadership (should fail - sticky)
    await node2.try_become_coordinator()
    assert node2.is_coordinator is False
    logger.info("✅ [Drill] Node 2 respected Node 1's sticky lease.")
    
    # 3. Node 1 "crashes" (we just don't refresh lease)
    logger.info("💥 [Drill] Simulating Node 1 crash (Stopping heartbeat)...")
    await asyncio.sleep(6) # Wait for lease to expire
    
    # 4. Node 2 tries to take leadership (should succeed)
    await node2.try_become_coordinator()
    assert node2.is_coordinator is True
    logger.info("👑 [Drill] Node 2 successfully promoted to COORDINATOR.")
    
    # 5. Clean up
    await node2.r.delete(node2.leader_key)
    logger.info("🔚 [Drill] Failover verified. Swarm state reset.")

if __name__ == "__main__":
    asyncio.run(simulate_swarm())
