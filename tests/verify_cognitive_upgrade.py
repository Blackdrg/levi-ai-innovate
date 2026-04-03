import asyncio
import os
import logging
from typing import Dict, Any

# Mocking for testing if dependencies are missing
try:
    from backend.services.agent_bus import sovereign_bus
    from backend.services.local_llm import local_llm
    from backend.core.workflow_engine import WorkflowEngine
    from backend.pipelines.learning import learning_system
except ImportError as e:
    print(f"Import Error: {e}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Verification")

async def test_agent_bus():
    logger.info("--- Testing Agent Bus ---")
    sovereign_bus.register("test_agent_1")
    sovereign_bus.register("test_agent_2")
    
    await sovereign_bus.send("test_agent_2", {"data": "Hello from 1", "from": "test_agent_1"})
    msg = await sovereign_bus.receive("test_agent_2")
    
    if msg and msg["data"] == "Hello from 1":
        logger.info("Agent Bus: SUCCESS")
    else:
        logger.error("Agent Bus: FAILED")

async def test_local_llm_status():
    logger.info("--- Testing Local LLM ---")
    path = os.getenv("LOCAL_MODEL_PATH", "models/llama-3.gguf")
    if os.path.exists(path):
        logger.info(f"Local Model found at {path}.")
        # We don't run inference here to avoid heavy load, just check initialization
        if local_llm.model_path == path:
            logger.info("Local LLM Initialization: SUCCESS")
    else:
        logger.warning(f"Local Model NOT found at {path}. This is expected if the user hasn't downloaded it yet.")

async def test_workflow_engine_config():
    logger.info("--- Testing Workflow Engine Configuration ---")
    os.environ["LEVI_WORKFLOW_MAX_ITERATIONS"] = "3"
    engine = WorkflowEngine()
    if engine.max_iterations == 3:
        logger.info("Workflow Engine Config: SUCCESS")
    else:
        logger.error(f"Workflow Engine Config: FAILED (Expected 3, got {engine.max_iterations})")

async def main():
    await test_agent_bus()
    await test_local_llm_status()
    await test_workflow_engine_config()
    logger.info("Verification Complete.")

if __name__ == "__main__":
    asyncio.run(main())
