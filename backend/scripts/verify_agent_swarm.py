import sys
import os
import asyncio
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.core.agent_registry import AgentRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SwarmVerifier")

REQUIRED_AGENTS = [
    "scout", "artisan", "librarian", "critic", "architect", 
    "chronicler", "sentinel", "vision", "echo", "analyst", 
    "curator", "messenger", "dreamer", "sovereign"
]

async def verify_swarm():
    logger.info("🕵️ [SwarmVerifier] Auditing Cognitive Agent Registry (v15.0)...")
    
    missing = []
    registered_count = 0
    
    for agent_name in REQUIRED_AGENTS:
        agent = AgentRegistry.get_agent(agent_name)
        if not agent:
            logger.error(f"❌ [SwarmVerifier] Agent MISSING: {agent_name}")
            missing.append(agent_name)
        else:
            logger.info(f"✅ [SwarmVerifier] Agent VALID: {agent_name} ({agent.agent_type})")
            registered_count += 1
            
    if missing:
        logger.error(f"💥 [SwarmVerifier] Swarm audit FAILED. {len(missing)} agents missing from registry.")
        sys.exit(1)
        
    logger.info(f"✨ [SwarmVerifier] Swarm audit SUCCESS. All {registered_count} agents verified and production-ready.")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(verify_swarm())
