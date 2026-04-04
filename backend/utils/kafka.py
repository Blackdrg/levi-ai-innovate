import json
import logging
import os
import asyncio
from typing import Any, Dict, Optional
try:
    from aiokafka import AIOKafkaProducer # type: ignore
    KAFKA_AVAILABLE = True
except ImportError:
    AIOKafkaProducer = None
    KAFKA_AVAILABLE = False

logger = logging.getLogger(__name__)

class SovereignKafka:
    """
    Sovereign Kafka Interface v8.
    Asynchronous event emission for the cognitive mission bus.
    Degrades gracefully if aiokafka is not installed.
    """
    _producer: Optional[Any] = None
    _loop = None

    @classmethod
    async def get_producer(cls) -> Optional[Any]:
        if not KAFKA_AVAILABLE:
            return None

        if cls._producer is None:
            kafka_url = os.getenv("KAFKA_URL", "kafka:29092")
            try:
                cls._producer = AIOKafkaProducer(
                    bootstrap_servers=kafka_url,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    acks='all'
                )
                await cls._producer.start()
                logger.info(f"Sovereign Kafka: Connected to bus at {kafka_url}")
            except Exception as e:
                logger.error(f"Sovereign Kafka: Connection failed to {kafka_url}: {e}")
                return None
        return cls._producer

    @classmethod
    async def emit_event(cls, topic: str, data: Dict[str, Any]):
        """Emits a cognitive event to the global mission bus."""
        if not KAFKA_AVAILABLE:
            logger.debug("[Kafka] aiokafka not installed. Event skipped.")
            return

        producer = await cls.get_producer()
        if producer:
            try:
                await producer.send_and_wait(topic, data)
                logger.debug(f"Kafka Event Emitted: [{topic}]")
            except Exception as e:
                logger.error(f"Kafka Emission Failure: {e}")

    @classmethod
    async def stop(cls):
        if cls._producer:
            await cls._producer.stop()
            cls._producer = None
            logger.info("Sovereign Kafka: Connection severed.")
