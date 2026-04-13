import asyncio
import logging
from backend.core.orchestrator import Orchestrator
from backend.services.voice.processor import SovereignLocalTTS

# Set up logging to observe the cognitive transitions
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("SovereignSimulation")

async def run_simulation():
    logger.info("🚀 Booting LEVI-AI Sovereign OS Simulation...")
    
    # 1. Boot Orchestrator (Phase 8: Connect All Loops triggers here)
    orchestrator = Orchestrator()
    await orchestrator.initialize()
    
    logger.info("⏳ Waiting 3 seconds for Evolution Dreaming Loop to spin up...")
    await asyncio.sleep(3)
    
    # 2. Trigger a highly complex mission
    # This engages Phase 1 (Local LLM), Phase 2 (Internal Knowledge), 
    # Phase 5 (Agent Autonomy), and Phase 7 (Load Shifting).
    mission_prompt = (
        "Research the latest advancements in local edge inference, "
        "write a python script to benchmark latency, and synthesize a final report."
    )
    
    logger.info(f"🎯 Dispatching Mission: '{mission_prompt}'")
    result = await orchestrator.handle_mission(
        user_input=mission_prompt,
        user_id="sim_user_001",
        session_id="sim_session_001"
    )
    
    logger.info(f"✅ Mission Result Status: {result.get('status')}")
    logger.info(f"🧠 Final Response:\n{result.get('response')}\n")
    
    # 3. Test Local TTS (Phase 6)
    logger.info("🔊 Testing Phase 6 Local TTS...")
    tts = SovereignLocalTTS()
    await tts.synthesize_and_play("Simulation complete. The Sovereign OS is fully operational.")
    logger.info("🏁 Simulation Concluded.")

if __name__ == "__main__":
    asyncio.run(run_simulation())