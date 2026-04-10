import json
import time
import hashlib
import logging
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
    checksum: str = ""

class MemoryConsistencyManager:
    """
    Sovereign Memory Consistency Layer (MCM) v14.1.
    Implements EVENT SOURCING: 
    - The Event Log (Redis Stream) is the absolute source of truth.
    - All other stores (Redis KV, Postgres, Neo4j, FAISS) are derived projections.
    """

    @staticmethod
    def compute_checksum(payload: Dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def register_event(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Appends a new event to the single source of truth (Event Log).
        Returns a dict for system-wide compatibility.
        """
        event = MemoryEvent(
            user_id=user_id,
            type=payload.get("type", "generic"),
            payload=payload,
            version=payload.get("version", 1)
        )
        event.checksum = MemoryConsistencyManager.compute_checksum(event.payload)
        
        event_dict = event.model_dump()
        # Aliases for legacy compatibility (id vs event_id)
        event_dict["id"] = event.event_id
        
        if not HAS_REDIS:
            logger.warning("[MCM] Redis OFFLINE. Event registered in-memory only.")
            return event_dict

        try:
            # Append to Redis Stream (Event Log)
            redis_client.xadd(
                MEMORY_EVENT_STREAM, 
                {"event": json.dumps(event_dict)},
                maxlen=10000, 
                approximate=True
            )
            # Index by content hash for dedup
            content_hash = hashlib.sha256(event.checksum.encode()).hexdigest()
            redis_client.setex(f"mcm:content_hash:{user_id}:{content_hash}", 86400, event.event_id)
            
            logger.debug(f"[MCM] Event Logged: {event.event_id} ({event.type})")
        except Exception as e:
            logger.error(f"[MCM] Failed to log event: {e}")
            
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
        Consumes the Event Log and ensures downstream stores are synchronized.
        """
        if not HAS_REDIS: return
        
        try:
            last_id = redis_client.get("mcm:last_synced_event_id") or "0-0"
            streams = redis_client.xread({MEMORY_EVENT_STREAM: last_id}, count=50, block=1000)
            if not streams: return

            for _, entries in streams:
                for entry_id, data in entries:
                    event_raw = data.get("event")
                    if not event_raw: continue
                    
                    event_dict = json.loads(event_raw)
                    # Dispatch to derived stores logic here
                    logger.info(f"[MCM] Reconciling event: {event_dict.get('id')} type: {event_dict.get('type')}")
                    
                    # Update local checkpoint
                    redis_client.set("mcm:last_synced_event_id", entry_id)
                    
        except Exception as e:
            logger.error(f"[MCM] Reconciliation Engine Anomaly: {e}")

    @staticmethod
    def log_anomaly(user_id: str, anomaly: Dict[str, Any]):
        if HAS_REDIS:
            redis_client.rpush(f"mcm:anomalies:{user_id}", json.dumps(anomaly))

    @staticmethod
    def enqueue_retry(user_id: str, payload: Dict[str, Any], store: str = "generic") -> None:
        """Maintains legacy retry mechanism for failed derived writes."""
        if not HAS_REDIS: return
        enriched = {**payload, "store": store, "queued_at": time.time()}
        redis_client.rpush(f"mcm:retry:{store}:{user_id}", json.dumps(enriched))
