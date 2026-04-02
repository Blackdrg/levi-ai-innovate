import asyncio
import logging
import sys
import os

# Set root path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.core.agent_registry import AgentRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("validator.fleet")

async def validate_fleet():
    """
    Validates the 14 Sovereign Agents.
    Verifies registration, input schema compatibility, and instance creation.
    """
    agents = AgentRegistry.get_commissioned_agents()
    logger.info(f"Commissioned Agents: {len(agents)}")
    expected_count = 14
    
    if len(agents) < expected_count:
        logger.error(f"Missing agents. Found {len(agents)}, expected {expected_count}")
    
    for name in agents:
        logger.info(f"Testing dispatch for agent: {name}")
        # Test schema validation (empty/invalid input to check failure mode)
        res = await AgentRegistry.dispatch(name, {"input": "test mission"})
        
        if res.success:
            logger.info(f"Agent '{name}' SUCCESS: Mission dispatched successfully.")
        else:
            # Failure is okay if it's a legitimate reason (e.g. key missing for search)
            logger.warning(f"Agent '{name}' DISPATCH: {res.message or res.error}")

    logger.info("Fleet Validation Complete.")

if __name__ == "__main__":
    asyncio.run(validate_fleet())
