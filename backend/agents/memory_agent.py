"""
Sovereign Memory Agent v9.
Adds Neo4j fallback path:
  - On Neo4j failure → write triplets to Redis key mem:pending:triplets
  - On Neo4j recovery → replay pending queue via replay_pending_triplets()
"""

import json
import logging
import time
from typing import Any, Dict

from pydantic import BaseModel, Field

from backend.agents.base import SovereignAgent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

PENDING_TRIPLETS_KEY = "mem:pending:triplets"
PENDING_TTL          = 60 * 60 * 24 * 7   # 7 days retention


class MemoryInput(BaseModel):
    input: str = Field(..., description="The query about past interactions or user traits")
    user_id: str = "guest"
    session_id: str = "default"


class MemoryAgent(SovereignAgent[MemoryInput, AgentResult]):
    """
    Sovereign Memory Architect v9.
    - Recalls user context via MemoryManager (FAISS + Neo4j graph).
    - Writes CitationBundle triplets from ResearchAgent to Neo4j.
    - On Neo4j outage, queues triplets to Redis mem:pending:triplets
      and replays them automatically on the next successful Neo4j connection.
    """

    def __init__(self):
        super().__init__("MemoryAgent")

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _run(self, input_data: MemoryInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        user_id    = input_data.user_id
        query      = input_data.input
        session_id = input_data.session_id

        self.logger.info("Recalling Memory Mission for %s: '%s'", user_id, query[:40])

        # ── 1. Attempt Neo4j recovery replay (non-blocking) ───────────
        await self._attempt_replay_pending()

        # ── 2. Engage Memory Vault ────────────────────────────────────
        from backend.memory.manager import MemoryManager
        memory_manager = MemoryManager()
        history    = await memory_manager.get_context(user_id)
        memory_data = await memory_manager.get_combined_context(user_id, session_id, query)

        traits        = memory_data.get("long_term", {}).get("traits", [])
        preferences   = memory_data.get("long_term", {}).get("preferences", [])
        semantic_hits = memory_data.get("semantic_results", [])

        # ── 3. Ingest any CitationBundle passed via kwargs ─────────────
        citation_bundle = kwargs.get("citation_bundle") or memory_data.get("citation_bundle")
        if citation_bundle:
            await self._ingest_citation_bundle(citation_bundle, user_id)

        # ── 4. Synthesis ──────────────────────────────────────────────
        summary_context = (
            f"User Archetype Traits: {', '.join(traits) if traits else 'Unknown'}\n"
            f"Observed Preferences: {', '.join(preferences) if preferences else 'Unknown'}\n"
            f"Recent Dialogue: {len(history)} mission fragments analysed."
        )

        system_prompt = (
            "You are the LEVI Memory Agent. Your role is to provide continuity and resonance.\n"
            "Use the crystallised context to address the user mission with historical depth.\n"
        )

        generator = SovereignGenerator()
        final_response = await generator.council_of_models([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Memory Context: {summary_context}\n\nMission: {query}"},
        ])

        return {
            "message": final_response,
            "data": {
                "traits_detected":   len(traits),
                "semantic_resonance": len(semantic_hits),
                "user_id":           user_id,
            },
        }

    # ------------------------------------------------------------------
    # CitationBundle → Neo4j triplet ingest
    # ------------------------------------------------------------------

    async def _ingest_citation_bundle(self, bundle: Any, user_id: str):
        """
        Converts a CitationBundle (dict or model) into Neo4j triplets.
        Each source becomes: (topic)-[SOURCED_FROM]->(url)
        On Neo4j failure, triplets are queued to Redis.
        """
        # Accept both dict and pydantic CitationBundle
        if hasattr(bundle, "model_dump"):
            bundle = bundle.model_dump()

        topic   = bundle.get("topic", "unknown")
        sources = bundle.get("sources", [])

        triplets = []
        for src in sources:
            triplets.append({
                "subject":  topic,
                "relation": "SOURCED_FROM",
                "object":   src.get("url", ""),
                "meta": {
                    "title":      src.get("title", ""),
                    "confidence": src.get("confidence", 0.0),
                    "tenant_id":  user_id,
                },
            })

        for t in triplets:
            await self._upsert_triplet_with_fallback(
                subject=t["subject"],
                relation=t["relation"],
                obj=t["object"],
                tenant_id=user_id,
            )

    async def _upsert_triplet_with_fallback(
        self,
        subject: str,
        relation: str,
        obj: str,
        tenant_id: str = "default",
    ):
        """
        Write a triplet to Neo4j.
        On Neo4j failure → enqueue to Redis mem:pending:triplets.
        """
        try:
            from backend.memory.graph_engine import GraphEngine
            engine = GraphEngine()
            await engine.upsert_triplet(
                user_id=tenant_id,
                subject=subject,
                relation=relation,
                obj=obj,
                tenant_id=tenant_id,
            )
            await engine.close()
        except Exception as exc:
            logger.warning(
                "[MemoryAgent] Neo4j unavailable (%s) — queuing triplet to Redis: (%s)-[%s]->(%s)",
                exc, subject, relation, obj,
            )
            await self._enqueue_pending_triplet(subject, relation, obj, tenant_id)

    # ------------------------------------------------------------------
    # Redis pending queue
    # ------------------------------------------------------------------

    async def _enqueue_pending_triplet(
        self, subject: str, relation: str, obj: str, tenant_id: str
    ):
        """Push a serialised triplet to the Redis pending queue."""
        record = json.dumps({
            "subject":   subject,
            "relation":  relation,
            "object":    obj,
            "tenant_id": tenant_id,
            "queued_at": time.time(),
        })
        try:
            from backend.db.redis import r as redis_sync, HAS_REDIS
            if HAS_REDIS and redis_sync:
                redis_sync.rpush(PENDING_TRIPLETS_KEY, record)
                redis_sync.expire(PENDING_TRIPLETS_KEY, PENDING_TTL)
                logger.info("[MemoryAgent] Triplet enqueued → %s", PENDING_TRIPLETS_KEY)
            else:
                logger.warning("[MemoryAgent] Redis unavailable — triplet will be lost.")
        except Exception as exc:
            logger.error("[MemoryAgent] Failed to enqueue to Redis: %s", exc)

    async def _attempt_replay_pending(self):
        """
        Non-blocking replay: if Neo4j is reachable and the pending queue is non-empty,
        drain and re-apply all queued triplets. Called at the start of every _run().
        """
        try:
            from backend.db.redis import r as redis_sync, HAS_REDIS
            if not HAS_REDIS or not redis_sync:
                return

            queue_len = redis_sync.llen(PENDING_TRIPLETS_KEY)
            if queue_len == 0:
                return

            logger.info("[MemoryAgent] Found %d pending triplets — attempting Neo4j replay.", queue_len)

            from backend.memory.graph_engine import GraphEngine
            engine = GraphEngine()

            # Test Neo4j connectivity with a lightweight Cypher ping
            driver = await engine.store.connect()
            async with driver.session() as _s:
                await _s.run("RETURN 1")   # raises immediately if Neo4j is down

            replayed = 0
            failed   = 0

            # Drain queue
            while True:
                raw = redis_sync.lpop(PENDING_TRIPLETS_KEY)
                if raw is None:
                    break
                try:
                    t = json.loads(raw)
                    await engine.upsert_triplet(
                        user_id=t["tenant_id"],
                        subject=t["subject"],
                        relation=t["relation"],
                        obj=t["object"],
                        tenant_id=t["tenant_id"],
                    )
                    replayed += 1
                except Exception as exc:
                    failed += 1
                    logger.warning("[MemoryAgent] Replay failed for triplet: %s — %s", raw[:80], exc)
                    # Re-queue failed triplets at the back so they aren't lost
                    redis_sync.rpush(PENDING_TRIPLETS_KEY, raw)
                    break   # stop draining if Neo4j is still unhealthy

            await engine.close()
            logger.info("[MemoryAgent] Replay complete — %d OK, %d re-queued.", replayed, failed)

        except Exception as exc:
            # Neo4j still down — silently abort replay
            logger.debug("[MemoryAgent] Neo4j replay skipped (Neo4j unreachable): %s", exc)
