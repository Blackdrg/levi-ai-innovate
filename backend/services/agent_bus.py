import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AgentBus:
    """
    Sovereign Agent Message Bus v8.
    Enables asynchronous, decoupled communication between cognitive agents.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentBus, cls).__new__(cls)
            cls._instance.queues = {}
        return cls._instance

    def register(self, agent_name: str):
        """Registers an agent to the bus by creating a dedicated queue."""
        if agent_name not in self.queues:
            self.queues[agent_name] = asyncio.Queue()
            logger.info(f"[AgentBus] Registered agent: {agent_name}")

    async def send(self, to_agent: str, message: Dict[str, Any]):
        """Sends a message to a specific agent's queue."""
        if to_agent in self.queues:
            await self.queues[to_agent].put(message)
            logger.debug(f"[AgentBus] Message sent to {to_agent}")
        else:
            logger.warning(f"[AgentBus] Agent '{to_agent}' not registered. Message dropped.")

    async def receive(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Wait for and retrieve a message from an agent's queue."""
        if agent_name in self.queues:
            logger.debug(f"[AgentBus] {agent_name} is waiting for message...")
            return await self.queues[agent_name].get()
        return None

    def get_status(self) -> Dict[str, Any]:
        """Returns the current state of the Agent Bus for telemetry."""
        return {
            "registered_agents": list(self.queues.keys()),
            "queue_sizes": {name: q.qsize() for name, q in self.queues.items()},
            "status": "online"
        }

# Global instance for easier access
sovereign_bus = AgentBus()
