import json
import logging
import asyncio
from typing import Any, Dict, Optional
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import os

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_URL", "localhost:9092")

class LeviKafkaClient:
    """
    LeviBrain v8: Kafka Event Client
    Handles event streaming between brain, memory, and agent services.
    """
    _producer: Optional[AIOKafkaProducer] = None

    @classmethod
    async def get_producer(cls) -> AIOKafkaProducer:
        if cls._producer is None:
            cls._producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            await cls._producer.start()
        return cls._producer

    @classmethod
    async def send_event(cls, topic: str, data: Dict[str, Any]):
        """Non-blocking event emission."""
        try:
            producer = await cls.get_producer()
            await producer.send_and_wait(topic, data)
            logger.info(f"[Kafka] Event sent to topic: {topic}")
        except Exception as e:
            logger.error(f"[Kafka] Failed to send event to {topic}: {e}")

    @classmethod
    async def consume_events(cls, topic: str, callback: Any):
        """Consumer loop for service tasks."""
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id="levi_brain_group",
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='earliest'
        )
        await consumer.start()
        try:
            async for msg in consumer:
                logger.info(f"[Kafka] Received event from {topic}")
                await callback(msg.value)
        finally:
            await consumer.stop()

# Helper for background task emission
async def emit_brain_event(event_type: str, payload: Dict[str, Any]):
    await LeviKafkaClient.send_event(f"brain.{event_type}", payload)
