from __future__ import annotations
import enum
import json
import time
from typing import Dict, Optional, Any, List
from backend.db.redis import r as redis_client, HAS_REDIS


class MissionState(str, enum.Enum):
    CREATED = "CREATED"
    PLANNED = "PLANNED"
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
    MissionState.PLANNED: [MissionState.SCHEDULED, MissionState.FAILED],
    MissionState.SCHEDULED: [MissionState.RUNNING, MissionState.FAILED],
    MissionState.RUNNING: [MissionState.VALIDATING, MissionState.FAILED],
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

    def initialize(self, initial: MissionState = MissionState.CREATED) -> None:
        data = {
            "mission_id": self.mission_id,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "state": initial.value,
            "history": [{"state": initial.value, "ts": time.time()}],
            "nodes": {},
        }
        self._save(data)

    def transition(self, new_state: MissionState) -> bool:
        data = self._load()
        curr = MissionState(data.get("state", MissionState.CREATED.value))
        allowed = _ALLOWED_TRANSITIONS.get(curr, [])
        if new_state not in allowed and new_state not in [MissionState.FAILED, MissionState.DEAD]:
            return False
        data["state"] = new_state.value
        hist = data.get("history", [])
        hist.append({"state": new_state.value, "ts": time.time()})
        data["history"] = hist
        self._save(data)
        return True

    def record_node(self, node_id: str, status: str, info: Optional[Dict[str, Any]] = None) -> None:
        data = self._load()
        nodes = data.get("nodes", {})
        node = nodes.get(node_id, {"events": []})
        node["events"].append({"status": status, "ts": time.time(), "info": info or {}})
        nodes[node_id] = node
        data["nodes"] = nodes
        self._save(data)

    @staticmethod
    def get_state(mission_id: str) -> Optional[str]:
        if not HAS_REDIS:
            return None
        raw: Any = redis_client.get(f"mission:state:{mission_id}")  # type: ignore[assignment]
        if not raw:
            return None
        try:
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            if not isinstance(raw, str):
                raw = str(raw)
            data = json.loads(raw)
            return data.get("state")
        except Exception:
            return None
