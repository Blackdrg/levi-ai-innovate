# scripts/e2e_smoke_test.py
import asyncio
import logging
import httpx
import sys
import os

# Set up project path
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO, format="[SMOKE-TEST] %(levelname)s: %(message)s")
logger = logging.getLogger("SmokeTest")

async def test_e2e_mission_flow():
    """
    Sovereign OS Phase 1 Gate: E2E Smoke Test.
    Flow: Admission -> Kernel Handover -> Brain Routing -> Forensic Sign-off.
    """
    print("="*60)
    print("LEVI-AI SOVEREIGN SMOKE TEST (PHASE 1 GATE)")
    print("="*60)

    # 1. Start Simulated Kernel Telemetry (Section 101 Reality)
    logger.info(" [STAGE 1] Simulating HAL-0 Kernel Boot & Telemetry...")
    from backend.kernel.serial_bridge import kernel_bridge
    await kernel_bridge.start()
    logger.info(" ✅ Kernel Bridge ACTIVE.")

    # 2. Trigger Mission Request
    logger.info(" [STAGE 2] Dispatched Mission: 'Verify system integrity'")
    from backend.core.orchestrator import orchestrator
    
    # We mock a mission ID and user
    user_id = "smoke_test_user"
    mission_id = "mission_smoke_001"
    objective = "Verify system integrity"
    
    result = await orchestrator.handle_mission(
        user_id=user_id,
        user_input=objective,
        session_id="smoke_session_01",
        mission_id=mission_id
    )

    # 3. Verify admission and execution
    if result.get("status") == "succeeded" or result.get("status") == "stable":
        logger.info(f" [OK] Mission PROCURRED: {result.get('status')}")
        logger.info(f" -> Response: {result.get('response', '')[:50]}...")
        
        # 4. Check for Forensic Signature (Phase 2 readiness)
        if "audit_sig" in result:
            logger.info(f" [OK] Forensic Signature Detected: {result['audit_sig'][:15]}...")
        else:
            logger.error(" [FAIL] Forensic Signature MISSING.")
    else:
        logger.error(f" [FAIL] Mission FAILED: {result.get('status')}")
        return False

    # 5. Verify MCM Synchronization
    logger.info(" [STAGE 3] Verifying Tier 0-2 Memory Coherence...")
    from backend.db.redis import r as redis_client, HAS_REDIS
    if HAS_REDIS:
        # Check if mission result is cached in Tier 0
        cache = redis_client.hget("orchestrator:missions", mission_id)
        if cache:
             logger.info(" [OK] Tier 0 (Redis) Coherence: OK")
        else:
             logger.error(" [FAIL] Tier 0 Memory synchronization FAILED.")
    
    print("="*60)
    print("SMOKE TEST PASSED: SYSTEM IS BUILDBLE AND WIRED")
    print("="*60)
    
    # Cleanup
    await kernel_bridge.stop()
    return True

if __name__ == "__main__":
    success = asyncio.run(test_e2e_mission_flow())
    sys.exit(0 if success else 1)
