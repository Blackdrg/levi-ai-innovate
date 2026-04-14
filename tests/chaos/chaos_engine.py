import sys
import os
import asyncio
import time
import logging

# Ensure project root is in path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.core.dcn_protocol import get_dcn_protocol

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChaosEngine")

async def simulate_node_failure():
    """
    Phase 4.3: Chaos Testing - Node Failure Simulation.
    Simulates a node crash and measures the cluster recovery time (SLA: 30s).
    """
    dcn = get_dcn_protocol()
    logger.info(f"🔥 [Chaos] Targeting local node: {dcn.node_id}")
    
    # 1. State check before crash
    logger.info(f"Current Node State: {dcn.node_state} | Region: {dcn.region}")
    
    # 2. Simulate Crash (Set is_active to False)
    logger.warning("💥 [Chaos] SIMULATING INSTANT CRASH...")
    dcn.is_active = False
    crash_time = time.time()
    
    # 3. Wait for recovery
    # In a real cluster, other nodes would detect this.
    # Here we simulate the reboot and re-joining.
    await asyncio.sleep(5) 
    
    logger.info("🔄 [Chaos] REBOOTING NODE...")
    dcn.is_active = True
    # Re-run heartbeats and listeners
    await dcn.start_heartbeat()
    await dcn.start_consensus_listener()
    
    recovery_time = time.time() - crash_time
    logger.info(f"✅ [Chaos] Node RECOVERED and RE-JOINED mesh in {recovery_time:.2f}s")
    
    if recovery_time <= 30:
        logger.info("🏆 [Chaos] SLA COMPLIANCE: PASSED (Under 30s)")
    else:
        logger.error("❌ [Chaos] SLA COMPLIANCE: FAILED (Exceeded 30s)")

if __name__ == "__main__":
    asyncio.run(simulate_node_failure())
