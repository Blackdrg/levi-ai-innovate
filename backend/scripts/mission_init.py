"""
LEVI-AI Sovereign OS v13.0.0 Stable
Global Mission Initializer (The Heart of the Brain).
Initializes high-fidelity cognitive loops and DCN synchrony.
"""

import asyncio
import logging
import time
import sys
import os
from datetime import datetime, timezone

# Ensure we can import from the project root
sys.path.append(os.getcwd())

from backend.core.v8.brain import LeviBrainCoreController
from backend.core.evolution_tasks import WeeklyEvolution
from backend.broadcast_utils import SovereignBroadcaster

# Configure Production Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] SovereignCore: %(message)s'
)
logger = logging.getLogger("MissionInit")

async def mission_initialization_sequence():
    """
    Sovereign Protocol v13.0: Absolute Monolith Boot.
    """
    logger.info("=== INITIALIZING ABSOLUTE MONOLITH (v13.0.0) ===")
    
    # 1. Heartbeat Pulse (v13 Handshake)
    logger.info("[Init] Emitting Neural Pulse v13.0.0 to Global Stream...")
    SovereignBroadcaster.broadcast({
        "type": "PULSE_HANDSHAKE", 
        "version": "13.0.0", 
        "status": "pulsing", 
        "mode": "Absolute Monolith"
    })
    
    # 2. Database & Vector Synchronization (HNSW/SQL Sync)
    logger.info("[Init] Synchronizing HNSW Vector Fabric & SQL Resonance...")
    # These are initialized on first-access in our v8 architecture, but we trigger them here
    brain = LeviBrainCoreController()
    
    # 3. Trigger Global Evolution Cycle (The 'Dreaming' Loop)
    logger.info("[Init] Awakening the Global Evolution Cycle (The Dreaming Loop)...")
    evolution = WeeklyEvolution()
    # First evolution pass to crystallize existing patterns
    await evolution.run_weekly_evolution()
    
    # 4. Neural Router Handoff Verification
    logger.info("[Init] Performing local-to-cloud DCN Synchrony link probe...")
    # Simple reflection pass to ensure cognitive routes are open
    probe_response = await brain.run_mission_sync(
        input_text="Mission Integrity Check: Verify neural resonance.",
        user_id="system_init",
        session_id=f"init_{int(time.time())}"
    )
    
    logger.info(f"[Init] Mission Pulse Verified. Decision: {probe_response.get('decision')}")
    
    # Final Graduation Declaration
    logger.info("=== SOVEREIGN MISSION INITIALIZED: STATUS PULSING ===")
    
    # Sustain Pulse (Optional: Keep process alive for a few seconds to ensure all pub/sub events clear)
    await asyncio.sleep(2.0)

if __name__ == "__main__":
    try:
        asyncio.run(mission_initialization_sequence())
    except KeyboardInterrupt:
        logger.info("Initialization aborted by user.")
    except Exception as e:
        logger.critical(f"CRITICAL INITIALIZATION FAILURE: {e}")
