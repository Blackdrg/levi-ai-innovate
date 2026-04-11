from __future__ import annotations
import enum
import json
import time
from typing import Dict, Optional, Any, List
from backend.db.redis import r as redis_client, HAS_REDIS


class MissionState(str, enum.Enum):
    CREATED = "CREATED"
    PLANNED = "PLANNED"
    EXECUTING = "EXECUTING"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    VALIDATING = "VALIDATING"
    PERSISTED = "PERSISTED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    COMPENSATED = "COMPENSATED"
    DEAD = "DEAD"

_ALLOWED_TRANSITIONS: Dict[MissionState, List[MissionState]] = {
    MissionState.CREATED: [MissionState.PLANNED, MissionState.FAILED],
    MissionState.PLANNED: [MissionState.EXECUTING, MissionState.SCHEDULED, MissionState.FAILED],
    MissionState.EXECUTING: [MissionState.VALIDATING, MissionState.FAILED],
    MissionState.SCHEDULED: [MissionState.RUNNING, MissionState.EXECUTING, MissionState.FAILED],
    MissionState.RUNNING: [MissionState.VALIDATING, MissionState.EXECUTING, MissionState.FAILED],
    MissionState.VALIDATING: [MissionState.PERSISTED, MissionState.FAILED],
    MissionState.PERSISTED: [MissionState.COMPLETE, MissionState.FAILED],
    MissionState.FAILED: [MissionState.COMPENSATED, MissionState.DEAD],
    MissionState.COMPENSATED: [MissionState.DEAD],
}


class CentralExecutionState:
    def __init__(self, mission_id: str, trace_id: Optional[str] = None, user_id: Optional[str] = None):
        self.mission_id = mission_id
        self.trace_id = trace_id or mission_id
        self.user_id = user_id or "unknown"

    @property
    def _key(self) -> str:
        return f"mission:state:{self.mission_id}"

    def _load(self) -> Dict[str, Any]:
        if not HAS_REDIS:
            return {}
        raw: Any = redis_client.get(self._key)  # type: ignore[assignment]
        if not raw:
            return {}
        try:
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            if not isinstance(raw, str):
                raw = str(raw)
            return json.loads(raw)
        except Exception:
            return {}

    def _save(self, data: Dict[str, Any]) -> None:
        if not HAS_REDIS:
            return
        redis_client.setex(self._key, 3600, json.dumps(data))

    def initialize(self, initial: MissionState = MissionState.CREATED, term: int = 0) -> None:
        now = time.time()
        data = {
            "mission_id": self.mission_id,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "baseline_tag": "v14.1.0-DCN-ENABLED",
            "state": initial.value,
            "idempotency_key": None,
            "history": [{"state": initial.value, "ts": now}],
            "nodes": {},
            "replay": {},
            "metadata": {
                "term": term,
                "updated_at": now
            }
        }
        self._save(data)

    def attach_metadata(self, **metadata: Any) -> None:
        data = self._load()
        existing_meta = data.get("metadata", {})
        existing_meta.update(metadata)
        data["metadata"] = existing_meta
        self._save(data)

    def transition(self, new_state: MissionState, term: Optional[int] = None) -> bool:
        data = self._load()
        curr = MissionState(data.get("state", MissionState.CREATED.value))
        allowed = _ALLOWED_TRANSITIONS.get(curr, [])
        if new_state not in allowed and new_state not in [MissionState.FAILED, MissionState.DEAD]:
            return False
        
        now = time.time()
        data["state"] = new_state.value
        hist = data.get("history", [])
        hist.append({"state": new_state.value, "ts": now})
        data["history"] = hist
        
        # Update DCN Metadata
        meta = data.get("metadata", {})
        if term is not None:
            meta["term"] = max(meta.get("term", 0), term)
        meta["updated_at"] = now
        data["metadata"] = meta
        
        self._save(data)
        return True

    def attach_replay_payload(self, payload: Dict[str, Any]) -> None:
        data = self._load()
        replay = data.get("replay", {})
        replay.update(payload)
        data["replay"] = replay
        self._save(data)

    def record_node(self, node_id: str, status: str, info: Optional[Dict[str, Any]] = None) -> None:
        data = self._load()
        nodes = data.get("nodes", {})
        node = nodes.get(node_id, {"events": []})
        node["events"].append({"status": status, "ts": time.time(), "info": info or {}})
        nodes[node_id] = node
        data["nodes"] = nodes
        self._save(data)

    @staticmethod
    def claim_idempotency(user_id: str, idempotency_key: str, mission_id: str, ttl_seconds: int = 900) -> bool:
        if not HAS_REDIS:
            return True
        claim_key = f"mission:{idempotency_key}:lock"
        # First attempt to claim (NX)
        claimed = redis_client.set(claim_key, mission_id, nx=True, ex=ttl_seconds)
        if not claimed:
            # If already claimed, refresh TTL (Sliding Window) per user request
            current_owner = redis_client.get(claim_key)
            if current_owner:
                redis_client.expire(claim_key, ttl_seconds)
        return bool(claimed)

    @staticmethod
    def clear_idempotency(user_id: str, idempotency_key: str) -> None:
        """Sovereign v14.2: Explicitly releases a mission lock for immediate retry."""
        if not HAS_REDIS:
            return
        redis_client.delete(f"mission:{idempotency_key}:lock")
        

    @staticmethod
    def get_claimed_mission(user_id: str, idempotency_key: str) -> Optional[str]:
        if not HAS_REDIS:
            return None
        raw: Any = redis_client.get(f"mission:{idempotency_key}:lock")
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        return str(raw) if raw else None

    @staticmethod
    def get_full_data(mission_id: str) -> Optional[Dict[str, Any]]:
        if not HAS_REDIS:
            return None
        raw: Any = redis_client.get(f"mission:state:{mission_id}")
        if not raw:
            return None
        try:
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        except Exception:
            return None
