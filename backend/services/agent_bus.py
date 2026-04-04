import logging
import json
from typing import Dict, Any, Optional
from backend.redis_client import cache

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
        """Registers an agent to the bus. Redis lists serve as queues automatically."""
        # Note: In Redis, we don't strictly need to 'register' to create a list,
        # but we track it for telemetry.
        if agent_name not in self.queues:
            self.queues[agent_name] = f"sovereign:bus:queue:{agent_name}"
            logger.info(f"[AgentBus] Registered agent: {agent_name}")

    async def send(self, to_agent: str, message: Dict[str, Any]):
        """Sends a message to a specific agent's queue in Redis and mirrors to Kafka."""
        # 1. Primary: Redis FIFO Queue
        client = cache.get_client()
        queue_key = f"sovereign:bus:queue:{to_agent.lower()}"
        try:
            client.lpush(queue_key, json.dumps(message))
            logger.debug(f"[AgentBus] Message sent to {to_agent} via Redis")
        except Exception as e:
            logger.error(f"[AgentBus] Redis send failure: {e}")

        # 2. Secondary: Kafka Event Broadcast (Phase 2 Duality)
        try:
            from backend.kafka_client import LeviKafkaClient
            await LeviKafkaClient.send_event(f"sovereign.agent.{to_agent.lower()}", message)
        except (ImportError, Exception) as e:
            logger.warning(f"[AgentBus] Kafka mirroring skipped or failed: {e}")

    async def receive(self, agent_name: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """Wait for and retrieve a message from an agent's queue in Redis."""
        client = cache.get_client()
        queue_key = f"sovereign:bus:queue:{agent_name.lower()}"
        
        try:
            # Using loop.run_in_executor to avoid blocking the event loop with Redis sync BRPOP
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, client.brpop, queue_key, timeout)
            
            if result:
                _, message_json = result
                return json.loads(message_json)
        except Exception as e:
            logger.error(f"[AgentBus] Receive failure: {e}")
            
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
