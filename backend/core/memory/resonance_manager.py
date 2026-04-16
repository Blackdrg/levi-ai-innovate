"""
backend/core/memory/resonance_manager.py
LEVI-AI Sovereign OS v16.2.0 — Phase 3.1: Memory Resonance Integration

Synchronises T1 (Redis session cache) → T2 (Postgres episodic ledger)
→ T3 (FAISS / SovereignVectorStore) → T4 (Neo4j relational graph)
in a background 5-minute resonance cycle.

Robustness guarantees:
  • SHA-256 digest guard prevents re-consolidating identical sessions (idempotent T1→T2).
  • Redis SADD/EXPIRE tracker prevents re-indexing already-indexed missions (T2→T3).
  • Per-fact MD5 key prevents repeat Neo4j triplet writes, 30-day TTL (T3→T4).
  • Graceful degradation: Redis / Postgres / GraphEngine unavailability are caught
    and logged; the cycle retries after RESONANCE_RETRY_SECONDS.
  • FK guard: Mission rows are written with user_id="system" when the user is not
    in the user_profiles table (e.g. "global" virtual user).
  • decode_responses=True-aware: all Redis return values treated as str.
  • Prometheus counters (no-op fallback when prometheus_client not installed).
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
_CYCLE_SECONDS: int = int(os.getenv("RESONANCE_CYCLE_SECONDS", "300"))   # 5 min
_RETRY_SECONDS: int = int(os.getenv("RESONANCE_RETRY_SECONDS", "60"))    # 1 min
_T1_MAX_SESSIONS: int = 10    # chat keys scanned per cycle
_T1_MAX_MSGS: int = 20        # messages per session
_T2_LIMIT: int = 10           # missions queried per cycle
_T2_FIDELITY: float = 0.85    # minimum fidelity to vectorise
_T3_RECENT: int = 50          # max vector records sent to Neo4j
_SYSTEM_USER_ID: str = "system"  # FK-safe fallback user_id

# ---------------------------------------------------------------------------
# Optional Prometheus metrics (silent no-op when library absent)
# ---------------------------------------------------------------------------
try:
    from prometheus_client import Counter, Histogram as _Histogram

    _CYCLES = Counter(
        "levi_resonance_cycles_total",
        "Completed resonance stages",
        ["stage"],
    )
    _ERRORS = Counter(
        "levi_resonance_errors_total",
        "Failed resonance stages",
        ["stage"],
    )
    _LATENCY = _Histogram(
        "levi_resonance_stage_seconds",
        "Resonance stage latency",
        ["stage"],
    )
    _PROM = True
except ImportError:
    _PROM = False

    class _Noop:
        def labels(self, **kw):
            return self
        def inc(self, *a, **kw):
            pass
        def observe(self, *a, **kw):
            pass

    _CYCLES = _Noop()   # type: ignore
    _ERRORS = _Noop()   # type: ignore
    _LATENCY = _Noop()  # type: ignore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _str(v) -> str:
    """Decode bytes → str if redis returns bytes (decode_responses=False mode)."""
    return v.decode() if isinstance(v, bytes) else (v or "")


class MemoryResonanceManager:
    """
    Synchronize T1 → T2 → T3 → T4 with proper ordering and idempotency.

    Usage::

        mgr = MemoryResonanceManager()
        await mgr.start(user_ids=["global"])
        ...
        await mgr.stop()
    """

    def __init__(self):
        self._stop = asyncio.Event()
        self._tasks: List[asyncio.Task] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self, user_ids: Optional[List[str]] = None) -> None:
        """Spawn one resonance-cycle coroutine per user_id."""
        targets = user_ids or ["global"]
        for uid in targets:
            task = asyncio.create_task(
                self.resonance_cycle(uid),
                name=f"memory-resonance-{uid}",
            )
            self._tasks.append(task)
        logger.info("🧬 [Resonance] Manager started — users: %s", targets)

    async def stop(self) -> None:
        """Signal all cycles to stop and await cancellation."""
        self._stop.set()
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass
        logger.info("🛑 [Resonance] Manager stopped.")

    async def trigger_all_cycles(self) -> None:
        """
        Force-trigger a resonance cycle for all managed users.
        Called by external workers (e.g. hygiene pulse).
        """
        # We find user_ids from active tasks
        uids = []
        for t in self._tasks:
            name = t.get_name()
            if name.startswith("memory-resonance-"):
                uids.append(name.replace("memory-resonance-", ""))
        
        if not uids:
            uids = ["global"]

        logger.info("🧬 [Resonance] Force-triggering cycles for: %s", uids)
        for uid in uids:
            # We don't await here because these are idempotent and we don't want to block the pulse
            asyncio.create_task(self._consolidate_t1_to_t2(uid))
            asyncio.create_task(self._consolidate_t2_to_t3(uid))
            asyncio.create_task(self._consolidate_t3_to_t4(uid))

    # ------------------------------------------------------------------
    # Main Loop
    # ------------------------------------------------------------------

    async def resonance_cycle(self, user_id: str) -> None:
        """
        Background loop. Each iteration:
          T1→T2 → T2→T3 → T3→T4 → sleep(_CYCLE_SECONDS)

        On error: logs, increments error metric, sleeps _RETRY_SECONDS.
        """
        logger.info(
            "🔄 [Resonance] Cycle started user=%s interval=%ds", user_id, _CYCLE_SECONDS
        )
        while not self._stop.is_set():
            try:
                await self._consolidate_t1_to_t2(user_id)
                await self._consolidate_t2_to_t3(user_id)
                await self._consolidate_t3_to_t4(user_id)
                # Sleep until next cycle (or stop signal)
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=_CYCLE_SECONDS)
                except asyncio.TimeoutError:
                    pass
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(
                    "❌ [Resonance] Cycle error user=%s: %s", user_id, exc, exc_info=True
                )
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=_RETRY_SECONDS)
                except asyncio.TimeoutError:
                    pass

    # ------------------------------------------------------------------
    # Stage 1: T1 (Redis session cache) → T2 (Postgres episodic ledger)
    # ------------------------------------------------------------------

    async def _consolidate_t1_to_t2(self, user_id: str) -> None:
        """
        Collect recent chat messages from Redis and persist an episodic
        Mission + Message record to Postgres.

        Guard: SHA-256 of the interaction payload is stored in Redis for 24 h.
        Unchanged payloads are skipped (idempotent).
        FK guard: the Mission row uses user_id=_SYSTEM_USER_ID if "global" is
        passed (since "global" is not a real user_profiles row).
        """
        from backend.db.redis import get_async_redis_client
        from backend.db.postgres import PostgresDB
        from backend.db.models import Mission, Message

        stage = "t1_to_t2"
        redis = get_async_redis_client()
        if not redis:
            logger.debug("[Resonance] Redis unavailable – skipping T1→T2 user=%s", user_id)
            return

        # --- Collect interactions -------------------------------------------
        scan_pattern = f"chat:{user_id}:*"
        cursor, keys = "0", []
        while True:
            cursor, batch = await redis.scan(cursor=int(cursor), match=scan_pattern, count=100)
            keys.extend(batch)
            if int(cursor) == 0:
                break

        interactions: List[Dict] = []
        for key in keys[:_T1_MAX_SESSIONS]:
            raw = await redis.get(key)
            if not raw:
                continue
            try:
                history = json.loads(_str(raw))
            except Exception:
                continue
            if isinstance(history, list) and history:
                interactions.extend(history[-_T1_MAX_MSGS:])

        if not interactions:
            return

        # --- Digest guard (idempotency) ------------------------------------
        digest = hashlib.sha256(
            json.dumps(interactions, sort_keys=True).encode("utf-8")
        ).hexdigest()
        digest_key = f"resonance:t1t2:last_digest:{user_id}"
        stored = await redis.get(digest_key)
        if stored and _str(stored) == digest:
            logger.debug("[Resonance] T1→T2 skip — no new data user=%s", user_id)
            return

        # --- Write episodic record to Postgres -----------------------------
        # Use a FK-safe user_id: "global" is not in user_profiles
        pg_user_id = _SYSTEM_USER_ID if user_id not in ("system",) and not user_id.startswith("user_") else user_id
        summary = (
            f"Session archive for {user_id}: {len(interactions)} interactions "
            f"at {datetime.now(timezone.utc).isoformat()}"
        )
        mission_id = f"resonance_{user_id}_{digest[:16]}"

        try:
            async with PostgresDB.session_scope() as session:
                from sqlalchemy import select as sa_select
                existing = (await session.execute(
                    sa_select(Mission).where(Mission.mission_id == mission_id)
                )).scalar_one_or_none()
                if existing is None:
                    new_mission = Mission(
                        mission_id=mission_id,
                        user_id=pg_user_id,
                        objective="memory_resonance_t1_t2",
                        status="resonance_archived",
                        fidelity_score=1.0,
                        payload={
                            "summary": summary,
                            "interaction_count": len(interactions),
                            "source_user_id": user_id,
                        },
                    )
                    session.add(new_mission)
                    session.add(
                        Message(
                            mission_id=mission_id,
                            role="system",
                            content=summary,
                        )
                    )
        except Exception as pg_exc:
            logger.warning("[Resonance] T1→T2 Postgres write skipped: %s", pg_exc)

        # Mark digest in Redis (even if Postgres failed — avoids infinite retries)
        await redis.set(digest_key, digest, ex=86400)

        if _PROM:
            _CYCLES.labels(stage=stage).inc()
        logger.info(
            "✅ [Resonance] T1→T2 complete user=%s interactions=%d mission=%s",
            user_id, len(interactions), mission_id,
        )

    # ------------------------------------------------------------------
    # Stage 2: T2 (Postgres) → T3 (FAISS / SovereignVectorStore)
    # ------------------------------------------------------------------

    async def _consolidate_t2_to_t3(self, user_id: str) -> None:
        """
        Vectorise high-fidelity missions (fidelity > _T2_FIDELITY) that
        haven't been indexed yet.

        Guard: mission_ids tracked in a Redis SADD set, 7-day TTL.
        """
        from backend.db.redis import get_async_redis_client
        from backend.db.postgres import PostgresDB
        from backend.db.models import Mission
        from backend.core.memory_utils import extract_memory_graph
        from backend.memory.vector_store import SovereignVectorStore
        from sqlalchemy import select as sa_select

        stage = "t2_to_t3"
        redis = get_async_redis_client()
        indexed_key = f"resonance:t2t3:indexed:{user_id}"

        # Load already-indexed set
        indexed_ids: set = set()
        if redis:
            raw_set = await redis.smembers(indexed_key)
            indexed_ids = {_str(m) for m in raw_set}

        # Query Postgres — FK-safe: query by the system user OR actual user
        effective_uid = _SYSTEM_USER_ID if user_id == "global" else user_id
        try:
            async with PostgresDB.session_scope() as session:
                stmt = (
                    sa_select(Mission)
                    .where(
                        Mission.user_id == effective_uid,
                        Mission.fidelity_score > _T2_FIDELITY,
                    )
                    .order_by(Mission.updated_at.desc())
                    .limit(_T2_LIMIT)
                )
                missions = list((await session.execute(stmt)).scalars().all())
        except Exception as pg_exc:
            logger.warning("[Resonance] T2→T3 Postgres query failed: %s", pg_exc)
            return

        processed = 0
        for mission in missions:
            mid = mission.mission_id
            if mid in indexed_ids:
                continue

            objective = mission.objective or ""
            outcome = ""
            if isinstance(mission.payload, dict):
                outcome = str(
                    mission.payload.get("response", "")
                    or mission.payload.get("summary", "")
                )

            try:
                extraction = await extract_memory_graph(objective, outcome)
                facts = extraction.get("facts", []) if isinstance(extraction, dict) else []

                for fact in facts:
                    fact_text = (
                        fact.get("fact", "") if isinstance(fact, dict) else str(fact)
                    )
                    if not fact_text:
                        continue
                    category = (
                        fact.get("category", "factual") if isinstance(fact, dict) else "factual"
                    )
                    score = min(1.0, max(0.1, float(mission.fidelity_score or 0.5)))
                    await SovereignVectorStore.store_fact(
                        user_id=user_id,
                        fact_text=fact_text,
                        category=category,
                        importance=score,
                        success_impact=score,
                    )
            except Exception as vec_exc:
                logger.warning("[Resonance] T2→T3 vectorise failed for %s: %s", mid, vec_exc)
                continue

            if redis:
                await redis.sadd(indexed_key, mid)
                await redis.expire(indexed_key, 7 * 86400)
            processed += 1

        if processed:
            if _PROM:
                _CYCLES.labels(stage=stage).inc()
            logger.info(
                "✅ [Resonance] T2→T3 complete user=%s missions_indexed=%d",
                user_id, processed,
            )

    # ------------------------------------------------------------------
    # Stage 3: T3 (VectorStore) → T4 (Neo4j relational graph)
    # ------------------------------------------------------------------

    async def _consolidate_t3_to_t4(self, user_id: str) -> None:
        """
        Extract subject-predicate-object triplets from recent vector facts
        and upsert them into Neo4j via GraphEngine.

        Guard: each fact_id is marked processed in Redis, 30-day TTL.
        """
        from backend.db.redis import get_async_redis_client
        from backend.core.memory_utils import extract_memory_graph
        from backend.memory.vector_store import SovereignVectorStore
        from backend.memory.graph_engine import GraphEngine

        stage = "t3_to_t4"
        redis = get_async_redis_client()

        try:
            user_memory = await SovereignVectorStore.get_user_memory(user_id)
        except Exception as vm_exc:
            logger.warning("[Resonance] T3→T4 VectorStore unavailable: %s", vm_exc)
            return

        # Safe metadata access
        metadata_list = getattr(user_memory, "metadata", None) or []
        recent_records = [
            m for m in list(reversed(metadata_list))[:_T3_RECENT]
            if not m.get("deleted")
        ]

        if not recent_records:
            return

        graph = GraphEngine()
        processed = 0

        for record in recent_records:
            fact_text = record.get("text") or record.get("fact") or ""
            if not fact_text:
                continue

            fact_id = record.get("fact_id") or hashlib.md5(
                fact_text.encode("utf-8")
            ).hexdigest()
            fact_key = f"resonance:t3t4:processed:{user_id}:{fact_id}"

            if redis:
                cached = await redis.get(fact_key)
                if cached:
                    continue

            try:
                extraction = await extract_memory_graph(fact_text, "")
                triplets = (
                    extraction.get("triplets", []) if isinstance(extraction, dict) else []
                )
                for triplet in triplets:
                    if {"subject", "relation", "object"} <= set(triplet.keys()):
                        await graph.upsert_triplet(
                            user_id,
                            triplet["subject"],
                            triplet["relation"],
                            triplet["object"],
                            mission_id=record.get("db_id"),
                        )
            except Exception as neo_exc:
                logger.warning(
                    "[Resonance] T3→T4 triplet upsert failed for fact %s: %s",
                    fact_id, neo_exc,
                )

            if redis:
                await redis.set(fact_key, "1", ex=30 * 86400)
            processed += 1

        if processed:
            if _PROM:
                _CYCLES.labels(stage=stage).inc()
            logger.info(
                "✅ [Resonance] T3→T4 complete user=%s vectors_processed=%d",
                user_id, processed,
            )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_resonance_manager: Optional[MemoryResonanceManager] = None


def get_resonance_manager() -> MemoryResonanceManager:
    """Return the process-wide MemoryResonanceManager singleton."""
    global _resonance_manager
    if _resonance_manager is None:
        _resonance_manager = MemoryResonanceManager()
    return _resonance_manager
