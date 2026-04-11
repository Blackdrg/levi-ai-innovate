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
    def __init__(self, mission_id: Optional[str] = None, trace_id: Optional[str] = None, user_id: Optional[str] = None):
        self.mission_id = mission_id
        self.trace_id = trace_id or mission_id
        self.user_id = user_id or "unknown"
        self.namespace = "orchestrator"

    @property
    def _key(self) -> str:
        return f"{self.namespace}:missions"

    def _load(self) -> Dict[str, Any]:
        if not (HAS_REDIS and self.mission_id):
            return {}
        raw: Any = redis_client.hget(self._key, self.mission_id)
        if not raw:
            return {}
        try:
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        except Exception:
            return {}

    def _save(self, data: Dict[str, Any]) -> None:
        if not (HAS_REDIS and self.mission_id):
            return
        redis_client.hset(self._key, self.mission_id, json.dumps(data))

    @classmethod
    async def load_state_on_boot(cls) -> Dict[str, Any]:
        """
        Sovereign v15.0: Hybrid Pod Recovery Logic.
        Recovers 'ACTIVE' missions from Redis (Tier-0) with SQL (Tier-2) fallback.
        """
        active = {}
        
        # 1. Primary: Redis Hash Truth
        if HAS_REDIS:
            try:
                all_redis = redis_client.hgetall("orchestrator:missions")
                for mid_bytes, data_bytes in all_redis.items():
                    try:
                        mid = mid_bytes.decode()
                        data = json.loads(data_bytes.decode())
                        if data.get("state") in [MissionState.CREATED, MissionState.PLANNED, MissionState.EXECUTING, MissionState.SCHEDULED, MissionState.RUNNING]:
                            active[mid] = data
                    except Exception: continue
            except Exception as e:
                logger.error(f"[Recovery] Redis hydration failure: {e}")

        # 2. Secondary: PostgreSQL Fallback (If Redis is empty or for baseline integrity)
        if not active:
            logger.info("[Recovery] Redis Tier-0 empty. Attempting Tier-2 PostgreSQL hydration...")
            try:
                from backend.db.postgres import PostgresDB
                from backend.db.models import Mission
                from sqlalchemy import select
                
                async with await PostgresDB.get_session() as session:
                    stmt = select(Mission).where(Mission.status.in_([
                        MissionState.CREATED.value, MissionState.PLANNED.value, 
                        MissionState.EXECUTING.value, MissionState.SCHEDULED.value, 
                        MissionState.RUNNING.value
                    ]))
                    res = await session.execute(stmt)
                    missions = res.scalars().all()
                    
                    for m in missions:
                        # Re-constitute minimal state from SQL payload
                        active[m.mission_id] = m.payload or {
                            "mission_id": m.mission_id,
                            "user_id": m.user_id,
                            "state": m.status,
                            "metadata": {"goal": m.objective}
                        }
                        # Seed Redis back if available
                        if HAS_REDIS:
                            redis_client.hset("orchestrator:missions", m.mission_id, json.dumps(active[m.mission_id]))
            except Exception as e:
                logger.error(f"[Recovery] SQL hydration failure: {e}")

        if active:
            logger.info(f"[Recovery] Hybrid mode: Recovered {len(active)} active missions.")
        return active

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
        
        # 🛡️ Graduation #22: SQL Partitioning for HA
        if new_state in [MissionState.COMPLETE, MissionState.FAILED, MissionState.DEAD]:
            from backend.utils.runtime_tasks import create_tracked_task
            create_tracked_task(self._sync_to_postgres(data), name=f"mission-sql-sync-{self.mission_id}")
            
        return True

    async def _sync_to_postgres(self, data: Dict[str, Any]):
        """Persists mission state to PostgreSQL for HA recovery and auditing."""
        try:
            from backend.db.postgres import PostgresDB
            from backend.db.models import Mission
            from sqlalchemy.dialects.postgresql import insert
            
            # Using raw SQL or ORM for upsert
            async with await PostgresDB.get_session() as session:
                async with session.begin():
                    stmt = insert(Mission).values(
                        mission_id=data["mission_id"],
                        user_id=data.get("user_id"),
                        objective=data.get("metadata", {}).get("goal", "unknown"),
                        status=data["state"],
                        fidelity_score=data.get("metadata", {}).get("fidelity_score", 0.0),
                        payload=data
                    ).on_conflict_do_update(
                        index_elements=["mission_id"],
                        set_={
                            "status": data["state"],
                            "payload": data,
                            "fidelity_score": data.get("metadata", {}).get("fidelity_score", 0.0)
                        }
                    )
                    await session.execute(stmt)
                    logger.debug(f"[SQL-Sync] Mission {self.mission_id} persisted to PostgreSQL.")
        except Exception as e:
            logger.error(f"[SQL-Sync] Failed persisting mission {self.mission_id}: {e}")

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
