import asyncio
import logging
from typing import Dict, Any, List, Callable, Awaitable
from collections import defaultdict

logger = logging.getLogger(__name__)

class AgentBus:
    """
    Sovereign v15.0: Inter-Agent Communication Bus.
    Enables agents to publish data pulses and subscribe to thematic streams.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentBus, cls).__new__(cls)
            cls._instance.subscribers = defaultdict(list)
            cls._instance.history = []
        return cls._instance

    async def publish(self, sender: str, channel: str, payload: Any):
        """Step 4.2: Publish a pulse to the bus."""
        pulse = {
            "sender": sender,
            "channel": channel,
            "payload": payload,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        logger.debug(f"🚌 [Bus] Pulse from {sender} on channel '{channel}'")
        self.history.append(pulse)
        if len(self.history) > 100: self.history.pop(0)

        tasks = []
        for callback in self.subscribers[channel]:
            tasks.append(callback(pulse))
        
        if tasks:
            await asyncio.gather(*tasks)

    def subscribe(self, channel: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Step 4.2: Subscribe an agent to a specific channel."""
        self.subscribers[channel].append(callback)
        logger.info(f"👂 [Bus] Subscriber added for channel: {channel}")

agent_bus = AgentBus()
