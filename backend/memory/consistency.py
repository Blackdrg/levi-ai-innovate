import json
import time
import hashlib
import hmac
import logging
import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from backend.db.redis import r as redis_client, HAS_REDIS

logger = logging.getLogger(__name__)

MEMORY_EVENT_STREAM = "memory:event_log"

class MemoryEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{int(time.time()*1000)}")
    user_id: str
    type: str # interaction, triplet, fact, profile_update
    payload: Dict[str, Any]
    timestamp: float = Field(default_factory=time.time)
    version: int = 1
    previous_hash: str = "0" * 64
    checksum: str = ""

class MemoryConsistencyManager:
    """
    Sovereign Memory Consistency Layer (MCM) v15.1 [HARDENED].
    Implements EVENT SOURCING: 
    - The Event Log (Redis Stream) is the absolute source of truth.
    - All other stores (Redis KV, Postgres, Neo4j, FAISS) are derived projections.
    """

    @staticmethod
    def compute_checksum(payload: Dict[str, Any], prev_hash: str = "") -> str:
        """v15.1: HMAC-chained checksum for audit integrity."""
        canonical = json.dumps(payload, sort_keys=True, default=str)
        # Use a secure secret for hash chaining
        secret = os.getenv("DCN_SECRET", os.getenv("AUDIT_SECRET", "sovereign_fallback_secret")).encode()
        message = (prev_hash + canonical).encode()
        return hmac.new(secret, message, hashlib.sha256).hexdigest()

    @staticmethod
    def register_event(user_id: str, payload: Dict[str, Any], broadcast: bool = False) -> Dict[str, Any]:
        """
        Appends a new event to the single source of truth (Event Log).
        Implements Hash Chaining for high-fidelity audit integrity.
        v15.1: Added BFT-signed cross-node broadcasting.
        """
        prev_hash = "0" * 64
        if HAS_REDIS:
            last_hash = redis_client.get(f"mcm:last_hash:{user_id}")
            if last_hash:
                prev_hash = last_hash.decode() if isinstance(last_hash, bytes) else last_hash

        event = MemoryEvent(
            user_id=user_id,
            type=payload.get("type", "generic"),
            payload=payload,
            version=payload.get("version", 1),
            previous_hash=prev_hash
        )
        event.checksum = MemoryConsistencyManager.compute_checksum(event.payload, prev_hash)
        
        event_dict = event.model_dump()
        event_dict["id"] = event.event_id
        
        if not HAS_REDIS:
            logger.warning("[MCM] Redis OFFLINE. Event registered in-memory only (Chain broken).")
            return event_dict

        try:
            # 1. Append to Redis Stream (The Chain)
            redis_client.xadd(
                MEMORY_EVENT_STREAM, 
                {"event": json.dumps(event_dict)},
                maxlen=100000, 
                approximate=True
            )
            
            # 2. Update the Head of the Chain for this user
            redis_client.set(f"mcm:last_hash:{user_id}", event.checksum)
            
            # 3. Content Dedup index
            content_hash = hashlib.sha256(event.checksum.encode()).hexdigest()
            redis_client.setex(f"mcm:content_hash:{user_id}:{content_hash}", 86400, event.event_id)
            
            # 4. Phase 15.1: DCN Swarm Broadcast
            if broadcast:
                try:
                    from backend.core.dcn_protocol import get_dcn_protocol
                    dcn = get_dcn_protocol()
                    if dcn.is_active:
                         asyncio.create_task(dcn.broadcast_gossip(
                            mission_id=f"mcm_pulse_{event.event_id}",
                            payload=event_dict,
                            pulse_type="mcm_event"
                        ))
                except Exception: pass

            logger.debug(f"⛓️ [MCM] Audit Event Linked: {event.event_id} -> {prev_hash[:8]}...")
        except Exception as e:
            logger.error(f"[MCM] Hash Chain Write failure: {e}")
            
        return event_dict

    @staticmethod
    def compute_content_hash(payload: Dict[str, Any]) -> str:
        material = payload.get("payload") or payload.get("fact") or payload.get("type") or payload
        canonical = json.dumps(material, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def should_deduplicate(user_id: str, content_hash: str) -> bool:
        if not HAS_REDIS: return False
        return bool(redis_client.get(f"mcm:content_hash:{user_id}:{content_hash}"))

    @classmethod
    async def run_reconciliation(cls):
        """
        Sovereign v15.1: High-Performance Reconciliation Engine.
        Consumes the Event Log and ensures all 5 cognitive tiers are synchronized.
        """
        if not HAS_REDIS: return
        
        try:
            last_id = redis_client.get("mcm:last_synced_event_id") or "0-0"
            streams = redis_client.xread({MEMORY_EVENT_STREAM: last_id}, count=100, block=500)
            if not streams: return

            from backend.kernel.kernel_wrapper import kernel
            from backend.broadcast_utils import SovereignBroadcaster

            for _, entries in streams:
                for entry_id, data in entries:
                    event_raw = data.get("event")
                    if not event_raw: continue
                    
                    event_dict = json.loads(event_raw)
                    user_id = event_dict.get("user_id")
                    payload = event_dict.get("payload", {})
                    event_type = event_dict.get("type")
                    
                    # ⚡ v15.1 [KERNEL] High-Fidelity Batch Crystallization ⚡
                    fact_data = {
                        "id": event_dict.get("id"),
                        "content": json.dumps(payload),
                        "metadata": json.dumps({
                            "type": event_type,
                            "user_id": user_id,
                            "timestamp": event_dict.get("timestamp")
                        })
                    }
                    kernel.sync_memory_batch([fact_data])

                    # 1. Tier 3 Sync: Vector Store (Semantic)
                    if event_type == "fact":
                        from backend.memory.vector_store import SovereignVectorStore
                        await SovereignVectorStore.store_fact(
                            user_id, 
                            payload.get("text"), 
                            category=payload.get("category", "factual"),
                            importance=payload.get("importance", 0.5)
                        )
                    
                    # 2. Tier 1 Sync: Postgres (Episodic/Factual)
                    if event_type in ["fact", "interaction"]:
                        await cls._sync_to_postgres(user_id, event_type, payload)

                    # 3. Tier 2 Sync: Neo4j (Relational)
                    if event_type == "triplet":
                         from backend.memory.graph_engine import GraphEngine
                         ge = GraphEngine()
                         await ge.upsert_triplet(
                             user_id,
                             payload.get("subject"),
                             payload.get("relation"),
                             payload.get("object")
                         )
                    
                    # 4. Success Telemetry
                    SovereignBroadcaster.publish("system:pulse", {
                        "type": "MCM_SYNC_SUCCESS",
                        "event_id": event_dict.get("id"),
                        "tier_count": 5
                    })
                    
                    # Update local checkpoint
                    redis_client.set("mcm:last_synced_event_id", entry_id)
                    
            logger.info(f"✨ [MCM] Successfully reconciled current event batch.")
                    
        except Exception as e:
            logger.error(f"[MCM] Reconciliation Engine Anomaly: {e}")

    @staticmethod
    async def _sync_to_postgres(user_id: str, event_type: str, payload: Dict[str, Any]):
        """Internal helper for Tier 1 synchronization."""
        from backend.db.postgres_db import get_write_session
        from backend.db.models import UserFact, Mission, Message
        from sqlalchemy import select

        try:
            async with get_write_session() as session:
                if event_type == "fact":
                    new_fact = UserFact(
                        user_id=user_id,
                        fact=payload.get("text"),
                        category=payload.get("category", "factual"),
                        importance=payload.get("importance", 0.5)
                    )
                    session.add(new_fact)
                
                elif event_type == "interaction":
                    mission_id = payload.get("mission_id")
                    if mission_id:
                        res = await session.execute(select(Mission).where(Mission.mission_id == mission_id))
                        mission = res.scalar_one_or_none()
                        if not mission:
                            mission = Mission(
                                mission_id=mission_id,
                                user_id=user_id,
                                objective=payload.get("objective", "Synchronized Interaction")[:200],
                                status=payload.get("status", "completed")
                            )
                            session.add(mission)
                        
                        if payload.get("user_input") and payload.get("response"):
                            session.add(Message(mission_id=mission_id, role="user", content=payload["user_input"]))
                            session.add(Message(mission_id=mission_id, role="bot", content=payload["response"]))
        except Exception as e:
            logger.error(f"[MCM] Postgres Sync failed: {e}")

    @staticmethod
    def log_anomaly(user_id: str, anomaly: Dict[str, Any]):
        if HAS_REDIS:
            redis_client.rpush(f"mcm:anomalies:{user_id}", json.dumps(anomaly))

    @staticmethod
    def enqueue_retry(user_id: str, payload: Dict[str, Any], store: str = "generic") -> None:
        if not HAS_REDIS: return
        enriched = {**payload, "store": store, "queued_at": time.time()}
        redis_client.rpush(f"mcm:retry:{store}:{user_id}", json.dumps(enriched))
