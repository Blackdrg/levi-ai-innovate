import logging
import asyncio
from datetime import datetime, timezone
import json
import os
import hashlib
import hmac
from typing import Dict, Any, Optional, List
from backend.db.redis import r as redis_client, HAS_REDIS
from backend.db.postgres_db import get_write_session
from backend.db.models import Message, Mission, UserFact, UserTrait
from backend.utils.runtime_tasks import create_tracked_task
from backend.services.arweave_service import arweave_audit

# Global Sync Gate: GCP Pub/Sub
try:
    from google.cloud import pubsub_v1
    HAS_PUBSUB = True
except ImportError:
    HAS_PUBSUB = False

logger = logging.getLogger(__name__)

class MemoryConsistencyManager:
    """
    Sovereign v16.0-GA: Unified Memory Consistency Manager (MCM).
    Harmonizes v14.2 (Streaming) and v15.1 (Event Sourcing) legacy implementations.
    The single source of truth for high-fidelity cognitive synchronization.
    """
    STREAM_NAME = "sovereign:memory:consistency"
    GROUP_NAME = "mcm_primary_group"
    CONSUMER_NAME = "mcm_consumer_1"
    
    def __init__(self):
        self._is_running = False
        self._process_task: Optional[asyncio.Task] = None
        self.region = os.getenv("ENVIRONMENT", "local-node")
        
        self.publisher = None
        self.subscriber = None
        
        if HAS_PUBSUB and os.getenv("GCP_PROJECT_ID"):
            try:
                self.publisher = pubsub_v1.PublisherClient()
                self.subscriber = pubsub_v1.SubscriberClient()
                logger.info(f"[MCM] Global Cognitive Pulse bridge initialized.")
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
        try:
            redis_client.xgroup_create(self.STREAM_NAME, self.GROUP_NAME, id="0", mkstream=True)
        except Exception:
            pass 

        self._process_task = create_tracked_task(self._synchro_loop(), name="mcm-consistency-loop")
        logger.info("[MCM] Unified Memory Consistency Manager active.")

    async def log_anomaly(self, user_id: str, anomaly: Dict[str, Any]):
        if HAS_REDIS:
            redis_client.rpush(f"mcm:anomalies:{user_id}", json.dumps(anomaly))

    @staticmethod
    def compute_content_hash(payload: Dict[str, Any]) -> str:
        material = payload.get("payload") or payload.get("fact") or payload.get("type") or payload
        canonical = json.dumps(material, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def should_deduplicate(user_id: str, content_hash: str) -> bool:
        if not HAS_REDIS: return False
        return bool(redis_client.get(f"mcm:content_hash:{user_id}:{content_hash}"))

    async def emit_event(self, event_type: str, user_id: str, session_id: str, payload: Dict[str, Any]):
        """Emits a cognitive event to the consistency stream (Real-time)."""
        if not HAS_REDIS:
            # Fallback to direct processing if Redis is down (Best effort)
            await self._process_event(event_type, user_id, session_id, payload, "local")
            return

        event = {
            "type": event_type,
            "user_id": user_id,
            "session_id": session_id,
            "data": json.dumps(payload),
            "timestamp": str(datetime.now(timezone.utc).timestamp()),
            "id": f"evt_{int(datetime.now(timezone.utc).timestamp()*1000)}"
        }
        
        # Add to Content Dedup index
        content_hash = self.compute_content_hash(payload)
        redis_client.setex(f"mcm:content_hash:{user_id}:{content_hash}", 86400, event["id"])
        
        redis_client.xadd(self.STREAM_NAME, event, maxlen=100000)
        logger.debug(f"[MCM] Emitted {event_type} for {user_id}")

    async def stop(self):
        self._is_running = False
        if self._process_task:
            self._process_task.cancel()
            try: await self._process_task
            except asyncio.CancelledError: pass

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
                        
                        await self._process_event(event_type, user_id, session_id, payload, self.region)
                        redis_client.xack(self.STREAM_NAME, self.GROUP_NAME, msg_id)

            except Exception as e:
                logger.error(f"[MCM] Consistency Loop Error: {e}")
                await asyncio.sleep(1)

    async def _process_event(self, event_type: str, user_id: str, session_id: str, payload: Dict[str, Any], source_region: str):
        """High-Fidelity Tiered Synchronization."""
        logger.info(f"[MCM] Synchronizing {event_type} for {user_id}")

        try: 
            # 1. Tier 2 Sync (Postgres)
            async with get_write_session() as session:
                if event_type == "interaction":
                    msg = Message(mission_id=session_id, role="user", content=payload.get("input", ""), timestamp=datetime.now(timezone.utc))
                    session.add(msg)
                    mission = await session.get(Mission, session_id)
                    if not mission:
                        mission = Mission(mission_id=session_id, user_id=user_id, objective=payload.get("input", "Sync")[:200], status="completed")
                        session.add(mission)

                elif event_type == "fact_extracted" or event_type == "fact":
                    facts = payload.get("facts", [payload])
                    for f in facts:
                        fact_obj = UserFact(user_id=user_id, fact=f.get("fact") or f.get("text"), category=f.get("category", "general"), importance=f.get("importance", 0.5))
                        session.add(fact_obj)

            # 2. Tier 3 Sync (Neo4j - Real-time Streaming)
            if event_type in ["triplet", "interaction"]:
                from backend.db.neo4j_client import Neo4jClient
                try:
                    if event_type == "triplet":
                         # Real-time triplet write
                         from backend.memory.graph_engine import GraphEngine
                         ge = GraphEngine()
                         await ge.upsert_triplet(user_id, payload.get("subject"), payload.get("relation"), payload.get("object"))
                    else:
                        await Neo4jClient.add_interaction(user_id=user_id, query=payload.get("input", ""), response=payload.get("response", ""), sync=True)
                except Exception as e:
                    logger.error(f"[MCM] Neo4j Streaming failed: {e}")

            # 3. Tier 4 Sync (Vector Stores)
            from backend.db.vector_store import SovereignVectorStore
            try:
                if event_type == "interaction":
                    await SovereignVectorStore.store_fact(user_id, f"Interaction: {payload.get('input')[:50]}...", category="interaction")
                elif event_type == "fact_extracted" or event_type == "fact":
                    facts = payload.get("facts", [payload])
                    for f in facts:
                        await SovereignVectorStore.store_fact(user_id, f.get("fact") or f.get("text"), category=f.get("category", "semantic"), importance=f.get("importance", 0.5))
            except Exception as e:
                logger.error(f"[MCM] Vector Sync failed: {e}")

        except Exception as e: 
            logger.error(f"[MCM] Persistence Failure: {e}")

    async def run_reconciliation(self):
        """Self-healing drift detection between Cache and SQL."""
        if not HAS_REDIS: return
        try:
            active_redis = redis_client.hgetall("orchestrator:missions")
            async with get_write_session() as session:
                from sqlalchemy import select
                for mid_bytes, data_bytes in active_redis.items():
                    mid = mid_bytes.decode()
                    data = json.loads(data_bytes.decode())
                    if data.get("state") in ["COMPLETE", "FAILED"]:
                        res = await session.execute(select(Mission).where(Mission.mission_id == mid))
                        if not res.scalar_one_or_none():
                            await self._process_event("interaction", data["user_id"], mid, data.get("replay", {}), self.region)
                
                # 🌐 Phase 16.1: Decentralized Snapshot Offloading
                snapshot_id = f"mcm_snap_{int(datetime.now(timezone.utc).timestamp())}"
                snapshot_data = {
                    "mission_count": len(active_redis),
                    "region": self.region,
                    "consistency_stream_tail": redis_client.xinfo_stream(self.STREAM_NAME).get("last-generated-id") if HAS_REDIS else "0"
                }
                await arweave_audit.anchor_snapshot(snapshot_id, snapshot_data)

        except Exception as e:
            logger.error(f"[MCM] Reconciliation anomaly: {e}")

    def enqueue_retry(self, user_id: str, payload: Dict[str, Any], store: str = "generic") -> None:
        if not HAS_REDIS: return
        enriched = {**payload, "store": store, "queued_at": datetime.now(timezone.utc).timestamp()}
        redis_client.rpush(f"mcm:retry:{store}:{user_id}", json.dumps(enriched))

mcm_service = MemoryConsistencyManager()
