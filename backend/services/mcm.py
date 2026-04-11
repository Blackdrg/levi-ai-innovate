# backend/services/mcm.py
import logging
import asyncio
import json
import os
from typing import Dict, Any, Optional
from backend.redis_client import r as redis_client, HAS_REDIS
from backend.utils.runtime_tasks import create_tracked_task

# Global Sync Gate: GCP Pub/Sub
try:
    from google.cloud import pubsub_v1
    HAS_PUBSUB = True
except ImportError:
    HAS_PUBSUB = False

logger = logging.getLogger(__name__)

class MemoryConsistencyManager:
    """
    Sovereign v14.2.0: Memory Consistency Manager (MCM).
    Synchronizes the 4-tier memory architecture using Redis Streams and GCP Pub/Sub.
    Ensures regional sovereignty with global cognitive continuity.
    """
    STREAM_NAME = "sovereign:memory:consistency"
    GROUP_NAME = "mcm_primary_group"
    CONSUMER_NAME = "mcm_consumer_1"
    
    # Global Pulse Settings
    PULSE_TOPIC = "sovereign-cognitive-pulse"
    
    def __init__(self):
        self._is_running = False
        self._process_task: Optional[asyncio.Task] = None
        self._pulse_task: Optional[asyncio.Task] = None
        self.region = os.getenv("GCP_REGION", "local-node")
        self.project_id = os.getenv("GCP_PROJECT_ID")
        
        self.publisher = None
        self.subscriber = None
        
        if HAS_PUBSUB and self.project_id:
            try:
                self.publisher = pubsub_v1.PublisherClient()
                self.subscriber = pubsub_v1.SubscriberClient()
                logger.info(f"[MCM] Global Cognitive Pulse bridge initialized for {self.region}.")
            except Exception as e:
                logger.warning(f"[MCM] Pub/Sub init failed: {e}. Global sync offline.")

    async def start(self):
        """Starts the MCM synchronization loops."""
        if not HAS_REDIS:
            logger.warning("[MCM] No Redis detected. Consistency loop disabled.")
            return

        if self._is_running:
            return

        self._is_running = True
        # 1. Initialize Local Stream
        try:
            redis_client.xgroup_create(self.STREAM_NAME, self.GROUP_NAME, id="0", mkstream=True)
        except Exception:
            pass # Already exists

        self._process_task = create_tracked_task(self._synchro_loop(), name="mcm-consistency-loop")
        
        # 2. Initialize Global Pulse Subscriber
        if self.subscriber:
            self._pulse_task = create_tracked_task(self._global_pulse_loop(), name="mcm-global-pulse-loop")
            
        logger.info("[MCM] Memory Consistency Manager started.")

    async def stop(self):
        """Stops the MCM synchronization loops."""
        self._is_running = False
        for task in [self._process_task, self._pulse_task]:
            if task:
                task.cancel()
                try: await task
                except asyncio.CancelledError: pass
        logger.info("[MCM] Memory Consistency Manager stopped.")

    async def emit_event(self, event_type: str, user_id: str, session_id: str, payload: Dict[str, Any], source_region: Optional[str] = None):
        """Emits a cognitive event to the consistency stream."""
        if not HAS_REDIS:
            return

        event = {
            "type": event_type,
            "user_id": user_id,
            "session_id": session_id,
            "data": json.dumps(payload),
            "source_region": source_region or self.region,
            "timestamp": str(asyncio.get_event_loop().time())
        }
        redis_client.xadd(self.STREAM_NAME, event)
        logger.debug(f"[MCM] Emitted {event_type} for {user_id}")

    async def _synchro_loop(self):
        """Background loop to consume memory events and sync tiers."""
        while self._is_running:
            try:
                messages = redis_client.xreadgroup(
                    self.GROUP_NAME, self.CONSUMER_NAME, {self.STREAM_NAME: ">"}, 
                    count=10, block=1000
                )
                if not messages: continue

                for stream, msgs in messages:
                    for msg_id, data in msgs:
                        event_type = data[b'type'].decode()
                        user_id = data[b'user_id'].decode()
                        session_id = data[b'session_id'].decode()
                        payload = json.loads(data[b'data'].decode())
                        source_region = data[b'source_region'].decode() if b'source_region' in data else self.region

                        await self._process_event(event_type, user_id, session_id, payload, source_region)
                        redis_client.xack(self.STREAM_NAME, self.GROUP_NAME, msg_id)

            except Exception as e:
                logger.error(f"[MCM] Consistency Loop Error: {e}")
                await asyncio.sleep(1)

    async def _global_pulse_loop(self):
        """Listens for cognitive pulses from other regions via GCP Pub/Sub."""
        subscription_path = self.subscriber.subscription_path(self.project_id, f"pulse-sub-{self.region}")
        
        def callback(message):
            try:
                data = json.loads(message.data.decode())
                # Deduplication: Ignore events originated from this region
                if data.get("source_region") == self.region:
                    message.ack()
                    return
                
                # Ingest into local consistency stream for regional processing
                # We use a wrapper that marks it as a global sync to avoid loops
                asyncio.run_coroutine_threadsafe(
                    self.emit_event(
                        data["type"], data["user_id"], data["session_id"], 
                        data["payload"], source_region=data["source_region"]
                    ),
                    asyncio.get_event_loop()
                )
                message.ack()
                logger.info(f"[MCM-Pulse] Received global pulse: {data['type']} from {data['source_region']}")
            except Exception as e:
                logger.error(f"[MCM-Pulse] Pulse ingestion failed: {e}")

        logger.info(f"[MCM-Pulse] Listening for global cognitive events on {subscription_path}")
        self.subscriber.subscribe(subscription_path, callback=callback)
        
        while self._is_running:
            await asyncio.sleep(10)

    async def _process_event(self, event_type: str, user_id: str, session_id: str, payload: Dict[str, Any], source_region: str):
        """Syncs cognitive tiers. If event is local, relays to Global Cloud Pulse."""
        logger.info(f"[MCM] Synchronizing {event_type} event for {user_id}")

        # 1. Regional Sync Logic
        # (Tier 3: Neo4j, Tier 4: Vector Store as previously implemented)
        # ... [Logic remains same for brevity in this replace call] ...
        
        # 2. Global Bridge Logic: If event originated HERE, relay to Pub/Sub
        if source_region == self.region and self.publisher and event_type in ["interaction", "trait_distilled"]:
            topic_path = self.publisher.topic_path(self.project_id, self.PULSE_TOPIC)
            pulse_data = {
                "type": event_type, "user_id": user_id, "session_id": session_id,
                "payload": payload, "source_region": self.region,
                "timestamp": str(asyncio.get_event_loop().time())
            }
            try:
                self.publisher.publish(topic_path, json.dumps(pulse_data).encode("utf-8"))
                logger.debug(f"[MCM] Relayed {event_type} to Global Cloud Pulse bus.")
            except Exception as e:
                logger.error(f"[MCM] Global Relay Failed: {e}")

        # Implementation core...
        if event_type == "interaction":
            from backend.db.neo4j_client import Neo4jClient
            try: await Neo4jClient.add_interaction(user_id, payload.get("input", ""), payload.get("response", ""), session_id=session_id)
            except Exception: pass
            
            from backend.memory.vector_store import SovereignVectorStore
            try: await SovereignVectorStore.store_fact(user_id, f"Interaction recorded in {source_region}: {payload.get('input')[:50]}...", category="interaction")
            except Exception: pass

        elif event_type == "trait_distilled":
            from backend.memory.vector_store import SovereignVectorStore
            try: await SovereignVectorStore.store_fact(user_id, payload.get("trait", ""), category="trait")
            except Exception: pass

mcm_service = MemoryConsistencyManager()

