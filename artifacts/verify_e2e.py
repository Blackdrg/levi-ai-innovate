import asyncio
import os
import logging
import sys

# Add root to sys.path
sys.path.append(os.getcwd())

# Force development mode for eager tasks
os.environ["ENVIRONMENT"] = "development"
os.environ["DISTRIBUTED_COGNITION"] = "true"

async def verify_e2e_mission():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("verify-e2e")
    
    logger.info("🧪 Starting Sovereign E2E Mission Verification...")
    
    from backend.main import orchestrator
    if not orchestrator:
        logger.error("❌ Orchestrator not found in main.")
        return
    
    await orchestrator.initialize()

    # Trigger a mission
    logger.info("📡 Dispatching mission: 'What is the capital of France?'")
    result = await orchestrator.handle_mission(
        user_input="What is the capital of France?",
        user_id="test_user",
        session_id="test_session"
    )
    
    logger.info(f"🎁 Mission Result: {result}")
    
    if result.get("status") == "success":
        logger.info("✅ E2E Mission Completed Successfully!")
    else:
        logger.error(f"❌ Mission failed or returned unexpected status: {result.get('status')}")

if __name__ == "__main__":
    asyncio.run(verify_e2e_mission())
