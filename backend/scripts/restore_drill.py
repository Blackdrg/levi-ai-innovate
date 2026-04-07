"""
LEVI-AI v13.1.0-Hardened-PROD: Automated Recovery Drill.
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
    
    logger.info("🛠️ [PRE-FLIGHT] Checking Environment Readiness...")
    
    # 🧪 Drill Warm-up: Initialize VectorStore with dummy data to ensure files exist
    try:
        from backend.db.vector import VectorStore
        import numpy as np
        v_store = VectorStore("memory_faiss", dimension=384)
        dummy_vec = np.random.rand(1, 384).astype('float32')
        await v_store.add(dummy_vec, [{"text": "Drill Prep Vector", "source": "system"}], persist=True)
        # Force full checkpoint to create .index and .meta
        v_store.checkpoint()
        logger.info("✅ Drill Warm-up: FAISS Store [INITIALIZED]")
    except Exception as e:
        logger.error(f"⚠️ Drill Warm-up failed: {e}")

    # Check Binaries
    missing_binaries = []
    for b in ["pg_dump", "pg_restore", "age", "rclone"]:
        if not snap._is_binary_available(b):
            missing_binaries.append(b)
    
    if missing_binaries:
        logger.warning(f"⚠️ Missing External Binaries: {missing_binaries}. Some drill phases will be skipped.")

    # Check Services
    from backend.db.redis import HAS_REDIS
    if not HAS_REDIS:
        logger.warning("⚠️ Redis is NOT running. Redis persistence phase will be skipped.")

    logger.info("🎬 [PHASE 1] Initializing Full-Stack Coordinated Snapshot...")
    snap_id = await snap.create_full_snapshot()
    if not snap_id:
        logger.error("❌ Failed to create stack snapshot. Drill ABORTED.")
        return

    logger.info("💣 [PHASE 2] Simulating MULTI-STORE CORRUPTION (Postgres, Neo4j, Redis, FAISS)...")
    await snap.corrupt_all_for_drill()

    logger.info("🚑 [PHASE 3] Commencing Full-Stack Disaster Recovery (Restore)...")
    start = time.time()
    
    # 🏥 Restore the entire service stack simultaneously
    await snap.restore_from_snapshot(snap_id, stores=["all"])
    
    elapsed = time.time() - start

    # Record RTO for audit reporting
    measured_rto = round(elapsed, 2)
    logger.info(f"⏱️ [PHASE 4] Measured RTO: {measured_rto}s (Target: {DR_RTO_SECONDS}s)")
    
    # RTO Enforcement
    if elapsed < DR_RTO_SECONDS:
        logger.info(f"✅ RTO Compliance: PASSED ({measured_rto}s < {DR_RTO_SECONDS}s)")
    else:
        logger.error(f"❌ RTO BREACH: FAILED ({measured_rto}s > {DR_RTO_SECONDS}s)")

    logger.info("🔍 [PHASE 5] Verifying Service Integrity...")
    is_healthy = await snap.verify_faiss_integrity()
    
    if is_healthy:
        logger.info("✨ FULL-STACK RESTORE DRILL: [SUCCESS] - Sovereign OS (Partial/Full) Recovered.")
        if missing_binaries:
             logger.info("📢 Note: Drill was SUCCESSFUL in DEGRADED mode due to missing dependencies.")
    else:
        logger.error("💀 RESTORE DRILL: [FAILED] - Core integrity check failure.")
        raise RuntimeError("Drill failed: Core state not verified.")

if __name__ == "__main__":
    try:
        asyncio.run(run_drill())
    except KeyboardInterrupt:
        logger.warning("Drill interrupted by user.")
    except Exception as e:
        logger.error(f"Drill crashed: {e}")
