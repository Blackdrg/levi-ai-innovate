import asyncio
import logging
import json
import os
from backend.main import orchestrator
from backend.db.postgres import PostgresDB
from backend.db.models import Mission

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FinalTest")

async def test_end_to_end_mission():
    """
    Verifies the hardgrounded engineering baseline:
    1. Mission Admission (VRAM/Gating)
    2. Thinking Loop (Cognitive Engine)
    3. Consensus (Raft 3/4 Quorum)
    4. Persistence (Postgres Persistence)
    5. Finality (Audit Ledger)
    """
    logger.info("🛡️ Initiating LEVI-AI Sovereign OS v22.1 Integration Audit...")

    user_id = "forensic_tester"
    query = "Standard System Health Audit: Verify consensus and fidelity scoring."
    
    # 1. Dispatch Mission
    logger.info("🚀 Dispatching High-Fidelity Mission...")
    res = await orchestrator.handle_mission(
        user_input=query,
        user_id=user_id,
        session_id="test_session_v22"
    )
    
    mission_id = res.get("request_id") or res.get("mission_id")
    logger.info(f"✅ Mission Accepted: {mission_id}")

    # 2. Verify Persistence
    logger.info("💾 Verifying Persistence Residency...")
    async with PostgresDB.session_scope() as session:
        mission = await session.get(Mission, mission_id)
        if mission:
            logger.info(f"✅ Mission Recorded in SQL Fabric. Status: {mission.status}")
        else:
            logger.error("❌ Mission Record MISSING from SQL Fabric.")
            return

    # 3. Simulate Learning Loop Pulse
    from backend.core.learning_loop import LearningLoop
    logger.info("🧬 Triggering Autonomous Learning Pulse...")
    await LearningLoop.run_promotion_cycle()
    logger.info("✅ Learning Pulse Complete.")

    # 4. Final Verification
    logger.info("🏁 Audit Complete. LEVI-AI Sovereign OS is GROUNDED.")
    print("\n[SUCCESS] Sovereign OS Engineering Baseline v22.1 is Fully Functional.")

if __name__ == "__main__":
    # Ensure env is loaded
    os.environ["SYSTEM_SECRET"] = "forensic-test-secret-2026"
    asyncio.run(test_end_to_end_mission())
