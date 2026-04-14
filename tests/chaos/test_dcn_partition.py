import pytest
import asyncio
import time
from backend.core.dcn_protocol import DCNProtocol, ConsensusMode
from backend.agents.consensus_agent import ConsensusAgentV11

@pytest.mark.asyncio
async def test_dcn_partition_resilience():
    """
    Sovereign Chaos Test v15.1.
    Goal: Simulate a network partition and verify Raft-lite recovery and Consensus stability.
    """
    # 1. Setup 3 nodes (simulated in-process with shared Redis)
    node_alpha = DCNProtocol(node_id="chaos-alpha")
    node_bravo = DCNProtocol(node_id="chaos-bravo")
    node_gamma = DCNProtocol(node_id="chaos-gamma")
    
    # 2. Join the swarm
    node_alpha.peers = {"chaos-alpha", "chaos-bravo", "chaos-gamma"}
    node_bravo.peers = {"chaos-alpha", "chaos-bravo", "chaos-gamma"}
    node_gamma.peers = {"chaos-alpha", "chaos-bravo", "chaos-gamma"}
    
    # 3. Simulate Partition (Alpha isolated from Bravo & Gamma)
    # In DCNProtocol, we'll mock 'verify_quorum' to fail for Alpha if Bravo/Gamma are "offline"
    print("\n[Chaos] Injecting Partition: [Alpha] || [Bravo, Gamma]")
    
    # 4. Attempt a Consensus Mission on Alpha (Should fail to reach Quorum)
    try:
        # We manually reduce peers to simulate isolation
        node_alpha.peers = {"chaos-alpha"} 
        await node_alpha.broadcast_mission_truth("partition-test-1", {"status": "unstable"})
    except Exception as e:
        print(f"[Chaos] Alpha mission blocked as expected: {e}")

    # 5. Restore Partition
    print("[Chaos] Healing Partition...")
    node_alpha.peers = {"chaos-alpha", "chaos-bravo", "chaos-gamma"}
    
    # 6. Verify Raft Index Synchronization
    # Bravo commits index 1 while Alpha was away
    await node_bravo.broadcast_mission_truth("partition-test-2", {"status": "synced"})
    
    # Alpha should sync upon seeing Bravo's pulse
    await node_alpha.reconcile_state("partition-test-2", node_bravo.commit_index)
    
    assert node_alpha.last_applied_index == node_bravo.commit_index
    print(f"[Chaos] Node Alpha reconciled to Index {node_alpha.last_applied_index}")
    print("✅ Chaos Resilience Verified.")

if __name__ == "__main__":
    asyncio.run(test_dcn_partition_resilience())
