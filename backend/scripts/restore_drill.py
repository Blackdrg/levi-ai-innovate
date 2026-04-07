"""
LEVI-AI v1.0.0-RC1: Automated Recovery Drill.
Simulates a critical store failure and verifies that the system can recover 
within the defined RTO (Recovery Time Objective) of 300s.

Usage: python -m backend.scripts.restore_drill
"""

import asyncio
import time
import logging
from backend.core.snapshot import SnapshotOrchestrator
from backend.config.system import DR_RTO_SECONDS

# Configure logging for the drill
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RestoreDrill")

async def run_drill():
    snap = SnapshotOrchestrator()

    logger.info("🎬 [PHASE 1] Initializing Coordinated Snapshot...")
    snap_id = await snap.create_full_snapshot()
    if not snap_id:
        logger.error("❌ Failed to create initial snapshot. Drill ABORTED.")
        return

    logger.info("💣 [PHASE 2] Simulating FAISS Store Corruption...")
    await snap.corrupt_faiss_for_test()

    logger.info("🚑 [PHASE 3] Commencing Disaster Recovery (Restore)...")
    start = time.time()
    
    # Attempt restoration of the critical vector store
    await snap.restore_from_snapshot(snap_id, stores=["faiss"])
    
    elapsed = time.time() - start

    logger.info(f"⏱️ [PHASE 4] Recovery metrics: {elapsed:.1f}s (RTO Target: {DR_RTO_SECONDS}s)")
    
    # RTO Enforcement
    if elapsed < DR_RTO_SECONDS:
        logger.info(f"✅ RTO Compliance: PASSED ({elapsed:.1f}s < {DR_RTO_SECONDS}s)")
    else:
        logger.error(f"❌ RTO BREACH: FAILED ({elapsed:.1f}s > {DR_RTO_SECONDS}s)")
        assert elapsed < DR_RTO_SECONDS, f"RTO breach! Recovery took {elapsed:.1f}s"

    logger.info("🔍 [PHASE 5] Verifying Recovered Integrity...")
    is_healthy = await snap.verify_faiss_integrity()
    
    if is_healthy:
        logger.info("✨ RESTORE DRILL: [SUCCESS]")
    else:
        logger.error("💀 RESTORE DRILL: [FAILED] - Store integrity check failed after restore.")
        raise RuntimeError("Drill failed: Integrity not restored.")

if __name__ == "__main__":
    try:
        asyncio.run(run_drill())
    except KeyboardInterrupt:
        logger.warning("Drill interrupted by user.")
    except Exception as e:
        logger.error(f"Drill crashed: {e}")
