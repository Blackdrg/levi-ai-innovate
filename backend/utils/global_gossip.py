import os
import json
import logging
import asyncio
from typing import Optional
from google.cloud import pubsub_v1
from backend.db.redis import get_async_redis_client, HAS_REDIS_ASYNC

# Lazy accessor – resolves to the async Redis client once the HA initializer runs.
def _get_redis():
    return get_async_redis_client()


logger = logging.getLogger(__name__)

class GlobalGossipBridge:
    """
    Sovereign Global DCN Bridge v14.1.0.
    Connects regional Redis gossip channels via a Global GCP Pub/Sub topic.
    Enables cross-region memory synchronization for diversified databases.
    """
    REDIS_CHANNEL = "swarm:sync:v14"
    TOPIC_ID = os.getenv("GCP_DCN_TOPIC", "sovereign-cognitive-pulse")
    PROJECT_ID = os.getenv("GCP_PROJECT_ID")


    def __init__(self):
        self.publisher = None
        self.subscriber = None
        self.topic_path = None
        self._bridge_tasks = []

    async def initialize(self):
        """Initializes GCP Pub/Sub client."""
        if not self.PROJECT_ID:
            logger.warning("[DCN-Bridge] PROJECT_ID missing. Global gossip disabled.")
            return

        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.topic_path = self.publisher.topic_path(self.PROJECT_ID, self.TOPIC_ID)
        
        logger.info(f"🌐 [DCN-Bridge] Global bridge initialized for topic {self.TOPIC_ID}")

    async def start(self):
        """Starts the bi-directional bridge (Redis -> PubSub and PubSub -> Redis)."""
        if not self.publisher:
            return

        # 1. Start Redis -> PubSub forwarder
        self._bridge_tasks.append(asyncio.create_task(self._redis_to_pubsub()))
        
        # 2. Start PubSub -> Redis listener
        self._bridge_tasks.append(asyncio.create_task(self._pubsub_to_redis()))
        
        logger.info("[DCN-Bridge] Global gossip streams connected.")

    async def _redis_to_pubsub(self):
        """Listens to local Redis and elevates high-fidelity fragments to the global topic."""
        client = _get_redis()
        if not client:
            logger.warning("[DCN-Bridge] No async Redis client — redis_to_pubsub disabled.")
            return
        pubsub = client.pubsub()
        await pubsub.subscribe(self.REDIS_CHANNEL)
        
        logger.info("[DCN-Bridge] Listening to local Redis for global elevation...")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    # Only elevate if fidelity is extreme or explicitly marked
                    if data.get("fidelity_s", 0) > 0.98 or data.get("is_global"):
                        logger.info(f"📤 [DCN-Bridge] Elevating fragment {data['fragment_id']} to global topic.")
                        self.publisher.publish(self.topic_path, message['data'].encode("utf-8"))
                except Exception as e:
                    logger.error(f"[DCN-Bridge] Elevation error: {e}")

    async def _pubsub_to_redis(self):
        """Listens to global Pub/Sub and ingests fragments into local Redis."""
        subscription_path = self.subscriber.subscription_path(
            self.PROJECT_ID, f"pulse-sub-{os.getenv('GCP_REGION', 'global')}"
        )

        
        def callback(message):
            try:
                # Fast forward to local Redis
                payload = message.data.decode("utf-8")
                loop = asyncio.get_event_loop()
                _client = _get_redis()
                if _client:
                    asyncio.run_coroutine_threadsafe(
                        _client.publish(self.REDIS_CHANNEL, payload), 
                        loop
                    )
                message.ack()
                logger.debug(f"📥 [DCN-Bridge] Ingested global fragment into local Redis.")
            except Exception as e:
                logger.error(f"[DCN-Bridge] Ingestion error: {e}")
                message.nack()

        # Listen in background (This uses the Google Cloud lib's thread-based listener)
        self.subscriber.subscribe(subscription_path, callback=callback)
        logger.info(f"[DCN-Bridge] Subscribed to global topic via {subscription_path}")

# Singleton instance
global_swarm_bridge = GlobalGossipBridge()
