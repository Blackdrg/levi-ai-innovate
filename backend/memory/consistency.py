import json
import time
import hashlib
from typing import Dict, Any, Optional, List
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
    def _content_hash_key(user_id: str, content_hash: str) -> str:
        return f"mcm:content_hash_index:{user_id}:{content_hash}"

    @staticmethod
    def register_event(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates or bumps a versioned memory event and stores it in Redis.
        """
        content_hash = payload.get("content_hash") or MemoryConsistencyManager.compute_content_hash(payload)
        if not HAS_REDIS:
            enriched = {
                **payload,
                "id": payload.get("id") or f"mem_{int(time.time()*1000)}",
                "version": payload.get("version", 1),
                "timestamp": time.time(),
                "content_hash": content_hash,
                "write_accepted": True,
            }
            return enriched

        item_id = payload.get("id") or f"mem_{int(time.time()*1000)}"
        key = MemoryConsistencyManager._event_key(user_id, item_id)
        existing_raw = redis_client.get(key)
        version = 1
        existing = {}
        if existing_raw:
            try:
                existing = json.loads(existing_raw)
                version = int(existing.get("version", 1)) + 1
            except Exception:
                version = 1
                existing = {}

        expected_version = payload.get("expected_version")
        if expected_version is not None and existing and int(expected_version) != int(existing.get("version", 0)):
            anomaly = {
                "user_id": user_id,
                "item_id": item_id,
                "reason": "version_conflict",
                "expected_version": expected_version,
                "actual_version": existing.get("version"),
                "timestamp": time.time(),
            }
            MemoryConsistencyManager.log_anomaly(user_id, anomaly)
            raise ValueError(f"Version conflict for memory item {item_id}")

        enriched = {
            **payload,
            "id": item_id,
            "version": version,
            "timestamp": time.time(),
            "checksum": MemoryConsistencyManager.compute_checksum(payload),
            "content_hash": content_hash,
            "write_accepted": True,
        }
        if existing and payload.get("previous_checksum") and payload.get("previous_checksum") != existing.get("checksum"):
            anomaly = {
                "user_id": user_id,
                "item_id": item_id,
                "reason": "checksum_mismatch",
                "previous_checksum": payload.get("previous_checksum"),
                "actual_checksum": existing.get("checksum"),
                "timestamp": time.time(),
            }
            MemoryConsistencyManager.log_anomaly(user_id, anomaly)
            raise ValueError(f"Checksum mismatch for memory item {item_id}")

        redis_client.setex(key, 3600, json.dumps(enriched))
        redis_client.setex(
            MemoryConsistencyManager._content_hash_key(user_id, content_hash),
            86400,
            item_id,
        )
        return enriched

    @staticmethod
    def compute_checksum(payload: Dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_content_hash(payload: Dict[str, Any]) -> str:
        material = payload.get("payload") or payload.get("fact") or payload.get("type") or payload
        canonical = json.dumps(material, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def should_deduplicate(user_id: str, content_hash: str, ttl: int = 600) -> bool:
        """
        Simple dedup check keyed by content hash.
        """
        if not HAS_REDIS:
            return False
        k = MemoryConsistencyManager._content_hash_key(user_id, content_hash)
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

    @staticmethod
    def enqueue_retry(user_id: str, payload: Dict[str, Any], store: str = "generic") -> None:
        if not HAS_REDIS:
            return
        enriched = {
            **payload,
            "store": store,
            "queued_at": time.time(),
        }
        redis_client.rpush(f"mcm:retry:{store}:{user_id}", json.dumps(enriched))

    @staticmethod
    def verify_source_of_truth(user_id: str, item_id: str, observed_checksum: str) -> bool:
        if not HAS_REDIS:
            return True
        raw = redis_client.get(MemoryConsistencyManager._event_key(user_id, item_id))
        if not raw:
            return False
        event = json.loads(raw)
        return event.get("checksum") == observed_checksum

    @staticmethod
    def verify_before_write(user_id: str, item_id: str, observed_checksum: str, expected_version: Optional[int] = None) -> bool:
        if not HAS_REDIS:
            return True
        raw = redis_client.get(MemoryConsistencyManager._event_key(user_id, item_id))
        if not raw:
            return expected_version in (None, 0, 1)
        event = json.loads(raw)
        checksum_matches = event.get("checksum") == observed_checksum
        version_matches = expected_version is None or int(event.get("version", 0)) == int(expected_version)
        if not checksum_matches or not version_matches:
            MemoryConsistencyManager.log_anomaly(
                user_id,
                {
                    "item_id": item_id,
                    "reason": "pre_write_verification_failed",
                    "observed_checksum": observed_checksum,
                    "stored_checksum": event.get("checksum"),
                    "expected_version": expected_version,
                    "stored_version": event.get("version"),
                    "timestamp": time.time(),
                },
            )
        return checksum_matches and version_matches

    @staticmethod
    def log_anomaly(user_id: str, payload: Dict[str, Any]) -> None:
        if not HAS_REDIS:
            return
        redis_client.rpush(f"mcm:anomalies:{user_id}", json.dumps(payload))

    @staticmethod
    def summarize_memory_state(events: List[Dict[str, Any]]) -> str:
        canonical = json.dumps(sorted(events, key=lambda item: (item.get("id", ""), item.get("version", 0))), sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
