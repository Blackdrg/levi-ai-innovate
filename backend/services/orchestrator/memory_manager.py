"""
backend/services/orchestrator/memory_manager.py

3-Layer Memory System for LEVI AI Brain.

Layer 1 — Short-term  (Redis)     : Current session messages, instant access
Layer 2 — Mid-term    (Firestore) : Recent interaction history across sessions
Layer 3 — Long-term   (Firestore) : Extracted semantic facts, vector-searched

All Firestore blocking calls are wrapped in asyncio.to_thread() to prevent
blocking the event loop.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.redis_client import get_conversation, save_conversation
from backend.firestore_db import db as firestore_db

logger = logging.getLogger(__name__)

# Timeout (seconds) for mid-term Firestore queries to prevent event-loop stalls
_MIDTERM_TIMEOUT = 3.0


class MemoryManager:
    """Manages 3 layers of contextual memory for LEVI AI interactions."""

    # ── Layer 1: Short-term (Redis) ─────────────────────────────────────────

    @staticmethod
    def _fetch_short_term(session_id: str) -> List[Dict[str, Any]]:
        """Sync helper — runs inside asyncio.to_thread."""
        return get_conversation(session_id)

    @staticmethod
    async def get_short_term_memory(session_id: str) -> List[Dict[str, Any]]:
        """Async wrapper: instant session awareness from Redis."""
        return await asyncio.to_thread(MemoryManager._fetch_short_term, session_id)

    # ── Layer 2: Mid-term (Firestore) ───────────────────────────────────────

    @staticmethod
    def _fetch_mid_term(user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Sync Firestore query — runs inside asyncio.to_thread."""
        if not user_id:
            return []
        try:
            docs = (
                firestore_db.collection("conversations")
                .where("user_id", "==", user_id)
                .order_by("updated_at", direction="DESCENDING")
                .limit(limit)
                .stream()
            )
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error("Error fetching mid-term memory for %s: %s", user_id, e)
            return []

    @staticmethod
    async def get_mid_term_memory(
        user_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Async: recent interaction history (pulse) from Firestore, with timeout guard."""
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(MemoryManager._fetch_mid_term, user_id, limit),
                timeout=_MIDTERM_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning("Mid-term memory query timed out for user %s", user_id)
            return []
        except Exception as e:
            logger.error("Mid-term memory retrieval failed: %s", e)
            return []

    # ── Layer 3: Long-term (Firestore + Vectors) ────────────────────────────

    @staticmethod
    async def get_long_term_memory(
        user_id: str, query: str = ""
    ) -> Dict[str, Any]:
        """Retrieve categorized semantic facts from Firestore via vector search."""
        default_shape: Dict[str, Any] = {
            "preferences": [],
            "traits": [],
            "history": [],
            "other": [],
            "profile": {},
            "relevant_facts": [],
        }
        if not user_id:
            return default_shape

        try:
            from .memory_utils import search_relevant_facts, prune_old_facts

            # Trigger 30-day pruning (maintenance, non-blocking)
            asyncio.create_task(prune_old_facts(user_id))

            relevant_facts = await search_relevant_facts(user_id, query, limit=10)
            return {
                "preferences": [
                    f["fact"] for f in relevant_facts if f["category"] == "preference"
                ],
                "traits":      [
                    f["fact"] for f in relevant_facts if f["category"] == "trait"
                ],
                "history":     [
                    f["fact"] for f in relevant_facts if f["category"] == "history"
                ],
                "other":       [
                    f["fact"] for f in relevant_facts if f["category"] == "factual"
                ],
                "profile":     {},
                "relevant_facts": relevant_facts,
            }
        except Exception as e:
            logger.error("Error fetching long-term memory for %s: %s", user_id, e)
            return default_shape

    # ── Combined Context ─────────────────────────────────────────────────────

    @staticmethod
    async def get_combined_context(
        user_id: str, session_id: str, query: str = ""
    ) -> Dict[str, Any]:
        """
        Parallel retrieval from all 3 memory layers, merged into a single
        context dict for the orchestrator pipeline.
        """
        short_term_task = MemoryManager.get_short_term_memory(session_id)
        mid_term_task   = MemoryManager.get_mid_term_memory(user_id, limit=3)
        long_term_task  = MemoryManager.get_long_term_memory(user_id, query)

        short_term, mid_term, long_term = await asyncio.gather(
            short_term_task, mid_term_task, long_term_task
        )

        # Derive interaction 'pulse' from most recent mood tag
        moods = [m.get("mood", "philosophical") for m in mid_term if m.get("mood")]
        pulse = moods[0] if moods else "stable"

        return {
            "history":           short_term,
            "long_term":         long_term,
            "mid_term":          mid_term,
            "interaction_pulse": pulse,
            "user_id":           user_id,
            "session_id":        session_id,
        }

    # ── Memory Storage (async — safe to call from asyncio.create_task) ───────

    @staticmethod
    async def store_memory(
        user_id: str, session_id: str, user_input: str, bot_response: str
    ) -> None:
        """
        Persist current interaction to Redis (short-term) and trigger
        a Firestore conversation log update (via to_thread).

        Must be async so it can be scheduled via asyncio.create_task().
        """
        def _sync_store():
            try:
                history = get_conversation(session_id)
                history.append({
                    "user":      user_input,
                    "bot":       bot_response,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                save_conversation(session_id, history, user_id=user_id)
            except Exception as e:
                logger.error("store_memory sync error: %s", e)

        await asyncio.to_thread(_sync_store)

    # ── Fact Extraction (background) ─────────────────────────────────────────

    @staticmethod
    async def process_new_interaction(
        user_id: str, user_input: str, bot_response: str
    ) -> None:
        """
        Background task: extract atomic facts from the interaction,
        deduplicate, and buffer them to Redis (flushed to Firestore by Celery Beat).
        """
        from .memory_utils import extract_facts, store_facts
        try:
            new_facts = await extract_facts(user_input, bot_response)
            if new_facts:
                await store_facts(user_id, new_facts)
        except Exception as e:
            logger.error("process_new_interaction failed for %s: %s", user_id, e)
