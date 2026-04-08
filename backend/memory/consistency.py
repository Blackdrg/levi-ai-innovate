import json
import time
from typing import Dict, Any, Optional
from backend.db.redis import r as redis_client, HAS_REDIS


class MemoryConsistencyManager:
    """
    Memory Consistency Layer (MCM).
    Redis is the runtime source of truth; other stores are derived.
    """
    @staticmethod
    def _event_key(user_id: str, item_id: str) -> str:
        return f"mcm:event:{user_id}:{item_id}"

    @staticmethod
    def register_event(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates or bumps a versioned memory event and stores it in Redis.
        """
        if not HAS_REDIS:
            enriched = {
                **payload,
                "id": payload.get("id") or f"mem_{int(time.time()*1000)}",
                "version": payload.get("version", 1),
                "timestamp": time.time(),
            }
            return enriched

        item_id = payload.get("id") or f"mem_{int(time.time()*1000)}"
        key = MemoryConsistencyManager._event_key(user_id, item_id)
        existing_raw = redis_client.get(key)
        version = 1
        if existing_raw:
            try:
                existing = json.loads(existing_raw)
                version = int(existing.get("version", 1)) + 1
            except Exception:
                version = 1

        enriched = {
            **payload,
            "id": item_id,
            "version": version,
            "timestamp": time.time(),
        }
        redis_client.setex(key, 3600, json.dumps(enriched))
        return enriched

    @staticmethod
    def should_deduplicate(user_id: str, content_hash: str, ttl: int = 600) -> bool:
        """
        Simple dedup check keyed by content hash.
        """
        if not HAS_REDIS:
            return False
        k = f"mcm:dedup:{user_id}:{content_hash}"
        if redis_client.get(k):
            return True
        redis_client.setex(k, ttl, "1")
        return False

    @staticmethod
    def schedule_gc(user_id: str, item_id: str, ttl_seconds: int = 86400) -> None:
        """
        Schedules TTL-based pruning marker for downstream collectors.
        """
        if not HAS_REDIS:
            return
        redis_client.setex(f"mcm:gc:{user_id}:{item_id}", ttl_seconds, "1")
