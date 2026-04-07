import asyncio
import os
import json
import logging
from backend.services.brain_service import brain_service
from backend.core.brain import LeviBrainV14

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BrainVerification")

async def verify_brain_v14():
    logger.info("Starting Brain v14.0 Verification Pulse...")
    
    # 1. Test Policy Generation for a simple query
    logger.info("--- Test 1: Simple Query (Greeting) ---")
    simple_query = "Hello LEVI, how are you today?"
    policy_simple = await brain_service.generate_policy(simple_query)
    logger.info(f"Simple Query Mode: {policy_simple.mode}")
    logger.info(f"Simple Query Enable: {policy_simple.enable}")
    
    assert policy_simple.mode == "FAST" or policy_simple.mode == "BALANCED"
    assert policy_simple.enable["neo4j"] == False

    # 2. Test Policy Generation for a complex query
    logger.info("--- Test 2: Complex Query (Research + Graph) ---")
    complex_query = "Deep research on the impact of quantum computing on cybersecurity, including graph analysis of recent threats."
    policy_complex = await brain_service.generate_policy(complex_query)
    logger.info(f"Complex Query Mode: {policy_complex.mode}")
    logger.info(f"Complex Query Enable: {policy_complex.enable}")
    
    assert policy_complex.mode == "RESEARCH" or policy_complex.mode == "DEEP"
    # Note: Neo4j might depend on the intent classifier's specific output
    
    # 3. Test End-to-End Orchestrator (Mocked Execution)
    logger.info("--- Test 3: Orchestrator Integration (v14 Flow) ---")
    brain = LeviBrainV14()
    
    # We'll use a simple query to ensure it doesn't try to call real external tools if it can solve internally
    result = await brain.run(
        user_input="Hi",
        user_id="test_user",
        session_id="test_session"
    )
    
    logger.info(f"Orchestrator Result Status: {result.get('status', 'success')}")
    logger.info(f"Orchestrator Mode: {result.get('mode')}")
    logger.info(f"Orchestrator Policy: {result.get('policy', {}).get('policy_id')}")
    
    assert "response" in result
    assert result["mode"] in ["FAST", "BALANCED", "DEEP", "RESEARCH", "SECURE"]

    logger.info("✅ Brain v14.0 Verification Completed Successfully.")

if __name__ == "__main__":
    asyncio.run(verify_brain_v14())
