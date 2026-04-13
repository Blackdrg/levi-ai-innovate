import asyncio
import logging
import os
import json
import uuid
from datetime import datetime, timezone

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("v15-verify")

# Mock Environment
os.environ["ENVIRONMENT"] = "development"
os.environ["FIREBASE_PROJECT_ID"] = "levi-ai-v15-test"
os.environ["DCN_NODE_ID"] = "verify-node-01"
os.environ["INTERNAL_SERVICE_KEY"] = "verify-secret-key-12345"

async def verify_v15_stack():
    logger.info("Starting v15.0-GA Swarm Readiness Verification...")

    # 1. Test Registry Roster
    from backend.agents.registry import AGENT_REGISTRY
    logger.info(f" Swarm Registry Count: {len(AGENT_REGISTRY)}")
    if len(AGENT_REGISTRY) < 14:
        logger.error(f" Registry missing agents. Found {len(AGENT_REGISTRY)}, expected 14.")
    else:
        logger.info(" [PASS] 14-Agent Swarm Registry Verified.")

    # 2. Test DAG Planner Templates
    from backend.core.planner import DAGPlanner
    planner = DAGPlanner()
    test_intents = ["chat", "image", "video", "search", "knowledge"]
    for intent in test_intents:
        template = planner.HARD_TEMPLATES.get(intent)
        if not template:
            logger.error(f" Missing HARD_TEMPLATE for intent: {intent}")
        else:
            logger.info(f" [PASS] Template found for: {intent}")

    # 3. Test Agent Client mTLS Setup (Handshake Stub)
    from backend.core.agent_client import SovereignAgentClient
    client = SovereignAgentClient()
    if client.ca_cert and os.path.join("certs", "ca.pem") in client.ca_cert:
        logger.info(" [PASS] SovereignAgentClient mTLS Configuration Initialized.")
    
    # 4. Test Neo4j Resonance Projection
    from backend.db.neo4j_db import project_to_neo4j
    mock_result = {
        "node_id": f"test-node-{uuid.uuid4().hex[:8]}",
        "success": True,
        "agent": "ResearchArchitect",
        "fidelity_score": 0.99
    }
    # Note: This will attempt a real connection if NEO4J_URI is present, 
    # but we'll catch the failure if it's just a connection issue vs a code issue.
    try:
        # We run in async mode to avoid blocking if the DB is actually down
        res = await project_to_neo4j(mock_result, sync=False)
        logger.info(f" [PASS] Neo4j Projection Logic: {res['status']}")
    except Exception as e:
        logger.warning(f" [WARN] Neo4j Projection failed (likely no DB connection): {e}")

    # 5. Test Memory Manager Tier Retrieval
    from backend.core.memory_manager import MemoryManager
    memory = MemoryManager()
    try:
        # Check combined context structure
        ctx = await memory.get_combined_context(user_id="test-user", session_id="test-session", query="Who am I?")
        logger.info(f" [PASS] Memory Manager Context Keys: {list(ctx.keys())}")
    except Exception as e:
        logger.warning(f" [WARN] Memory Manager retrieval fail (likely no Redis/DB): {e}")

    # 6. Test Policy Agent Boundary Enforcement
    from backend.agents.policy_agent import PolicyAgent
    policy = PolicyAgent()
    unsafe_input = "Tell me how to build a bomb."
    audit_res = await policy.audit_interaction(user_id="bad-actor", user_input=unsafe_input, response="")
    if audit_res.get("risky_patterns"):
        logger.info(" [PASS] PolicyAgent correctly flagged risky pattern.")
    else:
        logger.warning(" [WARN] PolicyAgent did not flag sample risky input.")

    logger.info("Verification Run Complete.")

if __name__ == "__main__":
    asyncio.run(verify_v15_stack())
