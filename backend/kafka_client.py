import logging
from typing import Any, Dict, Optional
import asyncio
from backend.utils.event_bus import sovereign_event_bus

logger = logging.getLogger(__name__)

class LeviKafkaClient:
    """
    Sovereign v16.2 Internalized Event Client.
    Redirects legacy Kafka calls to the local SovereignEventBus (Redis Streams).
    Fulfills Phase 3: 90% Internalization.
    """
    
    @classmethod
    async def get_producer(cls) -> Any:
        # Mocking for backward compatibility
        return sovereign_event_bus

    @classmethod
    async def send_event(cls, topic: str, data: Dict[str, Any]):
        """Internalized non-blocking event emission."""
        await sovereign_event_bus.emit(topic, data)

    @classmethod
    async def consume_events(cls, topic: str, callback: Any):
        """Internalized consumer bridge."""
        # We derive a group ID from the topic and service name for Redis
        group_id = f"consumer_group_{topic}"
        consumer_id = f"consumer_{topic}_{id(callback)}"
        await sovereign_event_bus.subscribe(topic, group_id, consumer_id, callback)

# Helper for background task emission
async def emit_brain_event(event_type: str, payload: Dict[str, Any]):
    await LeviKafkaClient.send_event(f"brain.{event_type}", payload)
