# backend/services/mcm.py
import logging
import asyncio
from datetime import datetime, timezone
import json
import os
from typing import Dict, Any, Optional
from backend.db.redis import r as redis_client, HAS_REDIS
from backend.db.postgres_db import get_write_session
from backend.db.models import Message, Mission, UserFact, UserTrait
from backend.utils.runtime_tasks import create_tracked_task

from backend.db.milvus_client import MilvusClient
from backend.db.vector_store import embed_text

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
        """Syncs cognitive tiers with LWW conflict resolution."""
        # 0. LWW (Last-Write-Wins) Resolution
        event_ts = float(payload.get("version", payload.get("timestamp", 0)))
        lww_key = f"mcm:last_seen:{user_id}:{event_type}"
        
        if HAS_REDIS:
            last_ts = redis_client.get(lww_key)
            if last_ts and float(last_ts) > event_ts:
                logger.info(f"[MCM] DROPPING stale {event_type} for {user_id} (Incoming: {event_ts} < Local: {last_ts})")
                return
            redis_client.set(lww_key, event_ts, ex=3600 * 24) # 24h retention for versioning
            
        logger.info(f"[MCM] Synchronizing {event_type} for {user_id} (v:{event_ts})")

        # 1. Regional Sync Logic
        
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

        # Implementation core (Hardened v15.0)
        try: 
            # 1. Tier 2 Sync (Postgres - Factual Persistent)
            async with get_write_session() as session:
                if event_type == "interaction":
                    # Store Interaction Message
                    msg = Message(
                        mission_id=session_id,
                        role="user",
                        content=payload.get("input", ""),
                        timestamp=datetime.now(timezone.utc)
                    )
                    session.add(msg)
                    
                    # Update/Create Mission
                    mission = await session.get(Mission, session_id)
                    if not mission:
                        mission = Mission(
                            mission_id=session_id,
                            user_id=user_id,
                            objective=payload.get("input", "Synchronized Interaction")[:200],
                            intent_type=payload.get("intent", "generic"),
                            status="completed"
                        )
                        session.add(mission)
                    else:
                        mission.status = "completed"
                        mission.updated_at = datetime.now(timezone.utc)

                elif event_type == "fact_extracted":
                    facts = payload.get("facts", [])
                    for f in facts:
                        fact_obj = UserFact(
                            user_id=user_id,
                            fact=f["fact"],
                            category=f.get("category", "general"),
                            importance=f.get("importance", 0.5)
                        )
                        session.add(fact_obj)

                elif event_type == "trait_distilled":
                    trait = payload.get("trait", "")
                    if trait:
                        trait_obj = UserTrait(
                            user_id=user_id,
                            trait=trait,
                            weight=payload.get("weight", 0.8)
                        )
                        session.add(trait_obj)

            # 2. Tier 3 Sync (Neo4j - Relational Knowledge)
            from backend.db.neo4j_client import Neo4jClient
            try:
                await Neo4jClient.add_interaction(
                    user_id=user_id, 
                    query=payload.get("input", ""), 
                    response=payload.get("response", ""), 
                    intent=payload.get("intent", "generic_sync"),
                    sync=True
                )
            except Exception as e:
                logger.error(f"[MCM] Neo4j Sync Failure: {e}")

            # 3. Tier 4 Sync (Vector Stores - Semantic)
            from backend.db.vector_store import SovereignVectorStore
            try:
                if event_type == "interaction":
                    await SovereignVectorStore.store_fact(user_id, f"Interaction: {payload.get('input')[:50]}...", category="interaction")
                    
                    # Global Milvus Relay
                    interaction_text = f"Input: {payload.get('input')} | Response: {payload.get('response')}"
                    vector = await asyncio.to_thread(embed_text, interaction_text)
                    await MilvusClient.store_global_fact(user_id, vector, {
                        "input": payload.get("input"), 
                        "response": payload.get("response"), 
                        "category": "interaction", 
                        "source_region": source_region
                    })
                
                elif event_type == "fact_extracted":
                    facts = payload.get("facts", [])
                    for f in facts:
                        await SovereignVectorStore.store_fact(user_id, f["fact"], category=f.get("category", "semantic"), importance=f.get("importance", 0.5))
                        vector = await asyncio.to_thread(embed_text, f["fact"])
                        await MilvusClient.store_global_fact(user_id, vector, {"fact": f["fact"], "category": "semantic", "source_region": source_region})
            except Exception as e:
                logger.error(f"[MCM] Vector Sync Failure: {e}")

        except Exception as e: 
            logger.error(f"[MCM] Tier 2 Persistence Failure: {e}")

    async def run_reconciliation(self):
        """
        Sovereign v15.0: Memory Reconciliation Pulse.
        Automated verification between Tier-0 (Redis) and Tier-2 (Postgres).
        Detects drift and heals the distributed state.
        """
        if not HAS_REDIS: return
        
        logger.info("[MCM] Initiating memory reconciliation pulse...")
        try:
            # 1. Fetch 'Active' missions from Redis
            active_redis = redis_client.hgetall("orchestrator:missions")
            
            # 2. Cross-reference with SQL truth for any missing or mismatching states
            from backend.db.postgres import PostgresDB
            from backend.db.models import Mission
            from sqlalchemy import select
            
            async with PostgresDB._session_factory() as session:
                for mid_bytes, data_bytes in active_redis.items():
                    mid = mid_bytes.decode()
                    data = json.loads(data_bytes.decode())
                    
                    if data.get("state") in ["COMPLETE", "FAILED"]:
                        # Verify it exists in SQL
                        stmt = select(Mission).where(Mission.mission_id == mid)
                        res = await session.execute(stmt)
                        if not res.scalar_one_or_none():
                            logger.warning(f"[MCM] Drift detected: Complete mission {mid} missing from SQL. Syncing...")
                            await self._process_event("interaction", data["user_id"], mid, data.get("replay", {}), self.region)

        except Exception as e:
            logger.error(f"[MCM] Reconciliation anomaly: {e}")

mcm_service = MemoryConsistencyManager()

