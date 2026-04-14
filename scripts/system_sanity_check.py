import asyncio
import logging
import time
import os
import json
from datetime import datetime

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("LEVI-AI-Sanity")

async def run_sanity_check():
    logger.info("🚀 Starting LEVI-AI Sovereign OS v15.2 Sanity Check...")
    start_time = time.time()
    
    # 1. Database & Persistence Tier Audit
    logger.info("📦 Auditing Persistence Tiers...")
    from backend.core.memory_manager import MemoryManager
    mem = MemoryManager()
    await mem.initialize()
    integrity = await mem.check_cognitive_integrity()
    
    for tier, status in integrity["tiers"].items():
        if status == "online":
            logger.info(f"✅ Tier {tier}: ONLINE")
        else:
            logger.warning(f"⚠️ Tier {tier}: {status.upper()}")

    # 2. Rust Microkernel Bridge Audit
    logger.info("⚙️ Auditing LeviKernel Bridge...")
    try:
        from backend.kernel.kernel_wrapper import kernel
        # We try a simple DAG validation (Self-loop detection)
        test_graph_id = f"sanity_check_{int(time.time())}"
        is_valid = kernel.validate_dag(test_graph_id)
        if is_valid:
            logger.info("✅ LeviKernel DAG Validator: STABLE")
        else:
            logger.error("❌ LeviKernel DAG Validator: FAILED (Cycle or Integrity Error)")
    except Exception as e:
        logger.error(f"❌ LeviKernel Bridge: FAILED ({e})")

    # 3. DCN Mesh & Consensus Audit
    logger.info("🛰️ Auditing DCN Mesh Consensus...")
    try:
        from backend.core.dcn_protocol import get_dcn_protocol
        dcn = get_dcn_protocol()
        health = await dcn.get_mesh_health()
        logger.info(f"✅ DCN Region: {health['region']} | Nodes: {health['active_nodes']} active")
        
        # Test BFT Signing
        test_pulse = dcn.sign_pulse("sanity_test", {"health": "ok"})
        if test_pulse.proof:
            logger.info("✅ BFT Ed25519 Signing: ACTIVE")
        else:
            logger.warning("⚠️ BFT Signing: FALLBACK (Kernel signing skipped)")
    except Exception as e:
        logger.error(f"❌ DCN Mesh Audit: FAILED ({e})")

    # 4. Cognitive Mission Simulation (Dry-Run)
    logger.info("🧠 Executing Cognitive Mission Simulation...")
    try:
        from backend.core.orchestrator import Orchestrator
        orc = Orchestrator()
        await orc.initialize()
        
        # We use a simple chat-mode mission to avoid heavy local inference during check
        result = await orc.handle_mission(
            user_input="LEVI, report status of the sovereign swarm.",
            user_id="sanity_user",
            session_id=f"sanity_sess_{int(time.time())}",
            bypass_cache=True,
            simplicity_mode=True # Use ultra-light mode
        )
        
        if result.get("status") == "success":
            logger.info(f"✅ Mission Simulation: SUCCESS (Latency: {result.get('latency', 'N/A')}ms)")
        else:
            logger.warning(f"⚠️ Mission Simulation: {result.get('status').upper()} ({result.get('response', 'No reason provided')})")
    except Exception as e:
        logger.error(f"❌ Mission Simulation: FAILED ({e})")

    # 5. Revolution UI Telemetry Pulse
    logger.info("📡 Testing Telemetry Pulse Broadcast...")
    try:
        from backend.broadcast_utils import SovereignBroadcaster
        SovereignBroadcaster.publish("system:pulse", {
            "type": "SANITY_CHECK_COMPLETED",
            "fidelity": integrity["overall_fidelity"],
            "timestamp": time.time()
        })
        logger.info("✅ Telemetry Pulse: BROADCASTED")
    except Exception as e:
        logger.error(f"❌ Telemetry Pulse: FAILED ({e})")

    duration = time.time() - start_time
    logger.info(f"🏁 Sanity Check Complete in {duration:.2f}s.")
    logger.info(f"📊 Overall System Fidelity: {integrity['overall_fidelity'] * 100}%")

if __name__ == "__main__":
    asyncio.run(run_sanity_check())
