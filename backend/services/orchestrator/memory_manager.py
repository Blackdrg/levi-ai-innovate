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
from backend.learning import UserPreferenceModel

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
        """Sync Firestore query with Redis caching — runs inside asyncio.to_thread."""
        if not user_id:
            return []
        
        from backend.redis_client import get_cached_json, cache_json
        cache_key = f"mid_term:{user_id}:{limit}"
        
        # 1. Try Redis cache
        cached = get_cached_json(cache_key)
        if cached is not None:
            return cached

        # 2. Fallback to Firestore
        try:
            docs = (
                firestore_db.collection("conversations")
                .where("user_id", "==", user_id)
                .order_by("updated_at", direction="DESCENDING")
                .limit(limit)
                .get() # Changed from .stream() to .get() for better error handling in sync thread
            )
            data = [doc.to_dict() for doc in docs]
            
            # 3. Cache in Redis (TTL = 10 mins)
            if data:
                cache_json(cache_key, data, ttl=600)
            return data
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
            # 1. Maintenance (Background)
            # consolidated garbage collection triggered based on interaction count (Phase 2 Hardened)
            from .memory_utils import search_relevant_facts, garbage_collect_index

            # 2. Vector Search (Immediate Buffer + Firestore)
            relevant_facts = await search_relevant_facts(user_id, query, limit=12)
            
            # 3. Categorization & Quality Filter (Phase 3 Hardened)
            # We only pull facts with high scores to ensure accuracy and relevance.
            facts = {
                "preferences": [f["fact"] for f in relevant_facts if f["category"] == "preference" and f["score"] > 0.70],
                "traits":      [f["fact"] for f in relevant_facts if f["category"] == "trait" and f["score"] > 0.70],
                "history":     [f["fact"] for f in relevant_facts if f["category"] == "history" and f["score"] > 0.75],
                "other":       [f["fact"] for f in relevant_facts if f["category"] == "factual" and f["score"] > 0.75],
                "profile":     {},
                "relevant_facts": relevant_facts,
            }
            
            # 4. Fetch High-Quality Learned Quotes (Phase 3)
            try:
                learned_docs = await asyncio.to_thread(
                    lambda: firestore_db.collection("quotes").where("topic", "==", "__learned__").limit(5).get()
                )
                facts["learned_knowledge"] = [d.to_dict().get("text") for d in learned_docs]
            except Exception:
                facts["learned_knowledge"] = []

            logger.info("[%s] LTM Retrieval: %d facts found.", user_id, len(relevant_facts))
            
            # 5. Token-Aware Trimming (LEVI v6 Phase 12)
            # We prune facts based on importance if the total context is too large.
            trimmed_facts = MemoryManager._trim_facts_by_tokens(facts, max_tokens=1500)
            return trimmed_facts
        except Exception as e:
            logger.error("Error fetching long-term memory for %s: %s", user_id, e)
            return default_shape

    @staticmethod
    def _trim_facts_by_tokens(facts: Dict[str, Any], max_tokens: int = 1500) -> Dict[str, Any]:
        """
        Intelligently prunes facts to fit within the token limit.
        Prioritizes: 
        1. Traits (High importance)
        2. Preferences
        3. History 
        4. Other
        """
        total_chars = 0
        categories = ["traits", "preferences", "history", "other"]
        pruned_facts = {cat: [] for cat in categories}
        pruned_facts["profile"] = facts.get("profile", {})
        pruned_facts["learned_knowledge"] = facts.get("learned_knowledge", [])
        
        # Approximate tokens: 4 chars = 1 token
        char_limit = max_tokens * 4
        
        for cat in categories:
            for fact in facts.get(cat, []):
                fact_len = len(str(fact))
                if total_chars + fact_len < char_limit:
                    pruned_facts[cat].append(fact)
                    total_chars += fact_len
                else:
                    break # Stop when we hit the limit
                    
        return pruned_facts

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

        # ── Phase 3: Cross-Service Bridge ────────────────────────────────────
        creation_task = MemoryManager.get_creation_context(user_id)
        
        short_term, mid_term, long_term, creation_context = await asyncio.gather(
            short_term_task, mid_term_task, long_term_task, creation_task
        )

        # ── Phase 2: Learner Integration ─────────────────────────────────────
        pref_model = UserPreferenceModel(user_id)
        preferences = await pref_model.get_profile()

        # Derive interaction 'pulse' from most recent mood tag
        moods = [m.get("mood", "philosophical") for m in mid_term if m.get("mood")]
        pulse = moods[0] if moods else preferences.get("preferred_moods", ["philosophical"])[0]

        # ── Phase 3: Drift Detection ─────────────────────────────────────────
        # Check if the user is pivoting topics rapidly (context drift)
        context_drift = False
        if len(short_term) > 1:
            recent_inputs = [m.get("user", "") for m in short_term[-3:]]
            # Simple heuristic: if input is very short and history is long, 
            # it might be a follow-up or a drift.
            if len(query.split()) < 3 and len(recent_inputs) > 0:
                context_drift = True

        return {
            "history":           short_term,
            "long_term":         long_term,
            "mid_term":          mid_term,
            "creation_context":  creation_context,
            "interaction_pulse": pulse,
            "preferences":       preferences,
            "user_id":           user_id,
            "session_id":        session_id,
            "context_drift":     context_drift
        }

    @staticmethod
    async def get_creation_context(user_id: str) -> List[Dict[str, Any]]:
        """
        LEVI v6 Phase 3: Fetch recent Studio creations and Gallery activity
        with Redis caching.
        """
        if not user_id or str(user_id).startswith("guest:"):
            return []
            
        from backend.redis_client import get_cached_json, cache_json
        cache_key = f"creation_ctx:{user_id}"
        
        # 1. Try Redis cache
        cached = get_cached_json(cache_key)
        if cached is not None:
            return cached

        try:
            # 2. Fetch last 3 successful Studio creations
            jobs = await asyncio.to_thread(
                lambda: firestore_db.collection("jobs")
                .where("user_id", "==", user_id)
                .where("status", "==", "completed")
                .order_by("completed_at", direction="DESCENDING")
                .limit(3).get()
            )
            
            creations = []
            for doc in jobs:
                data = doc.to_dict()
                creations.append({
                    "service": "studio",
                    "type":    data.get("type", "image"),
                    "prompt":  data.get("prompt", ""),
                    "result":  data.get("result_url", ""),
                    "timestamp": data.get("completed_at")
                })
            
            # 3. Cache in Redis (TTL = 15 mins)
            if creations:
                cache_json(cache_key, creations, ttl=900)
                
            return creations
        except Exception as e:
            logger.warning(f"Creation context retrieval failed for {user_id}: {e}")
            return []

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
                from backend.redis_client import get_conversation, save_conversation_buffered
                history = get_conversation(session_id)
                history.append({
                    "user":      user_input,
                    "bot":       bot_response,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                # Use buffered save to minimize Firestore costs
                save_conversation_buffered(session_id, history, user_id=user_id)
            except Exception as e:
                logger.error("store_memory sync error: %s", e)

        await asyncio.to_thread(_sync_store)

    # ── LEVI v6: Evolutionary Distillation ──────────────────────────────────────
    @staticmethod
    async def distill_core_memory(user_id: str) -> None:
        """
        Background task: Identifying clusters of fragmented facts and 
        distilling them into unified core traits (Silent v6 Evolution).
        """
        from .memory_utils import search_relevant_facts, store_facts
        from backend.services.orchestrator.planner import call_lightweight_llm
        import json

        try:
            # 1. Fetch recent/diverse facts to identify patterns
            facts = await search_relevant_facts(user_id, query="user personality and values", limit=25)
            if len(facts) < 10:
                return # Not enough material for high-fidelity distillation

            # Filter for facts that haven't been distilled yet or are low-importance updates
            fact_strings = "\n".join([f"- {f['fact']} (Importance: {f.get('importance', 0.5)})" for f in facts])
            
            # 2. LLM Synthesis of Core Persona
            prompt = (
                "You are the LEVI Core Distiller. Analyze these fragmented user facts and distill them into "
                "3-5 deep, high-level core identity traits or permanent preferences.\n"
                "Focus on 'Who they are' vs 'What they said'.\n\n"
                f"Facts:\n{fact_strings}\n\n"
                "Output ONLY JSON: {\"distilled_traits\": [{\"fact\": \"...\", \"importance\": 0.95}]}"
            )

            raw_json = await call_lightweight_llm([{"role": "system", "content": prompt}])
            if "```json" in raw_json: raw_json = raw_json.split("```json")[1].split("```")[0]
            
            data = json.loads(raw_json.strip())
            new_traits = data.get("distilled_traits", [])
            
            if new_traits:
                # 3. Store distilled traits as high-priority 'trait' category
                for trait in new_traits:
                    trait["category"] = "trait"
                
                await store_facts(user_id, new_traits)
                logger.info(f"[MemoryManager] Evolutionary Distillation: Consolidated {len(facts)} points into {len(new_traits)} core traits for {user_id}")

        except Exception as e:
            logger.error(f"Memory distillation failed for {user_id}: {e}")

    # ── Fact Extraction (background) ─────────────────────────────────────────

    @staticmethod
    async def process_new_interaction(
        user_id: str, user_input: str, bot_response: str
    ) -> None:
        """
        Background task: extract atomic facts from the interaction,
        grade them by importance, and buffer them for storage.
        """
        from .memory_utils import extract_facts, store_facts
        from backend.services.orchestrator.planner import call_lightweight_llm
        import json

        try:
            # 1. Extraction (Atomic)
            new_facts = await extract_facts(user_input, bot_response)
            if not new_facts:
                return

            # 2. Importance Scoring (v6)
            # We grade facts to distinguish 'Core Traits' from 'Fragmented Data'.
            fact_list = [f["fact"] for f in new_facts]
            scoring_prompt = (
                "You are the LEVI Memory Grader. Grade these facts on a scale of 0.0 to 1.0 based on "
                "how much they reveal about the user's permanent identity, core preferences, or deep history.\n"
                "- 0.1: Casual/Temporary (e.g. 'user is hungry')\n"
                "- 0.9: Core/Permanent (e.g. 'user values stoic philosophy')\n\n"
                f"Facts:\n{json.dumps(fact_list)}\n"
                "Output ONLY JSON: {\"scores\": [0.2, 0.9, ...]}"
            )
            
            try:
                raw_json = await call_lightweight_llm([{"role": "system", "content": scoring_prompt}])
                if "```json" in raw_json: raw_json = raw_json.split("```json")[1].split("```")[0]
                scores = json.loads(raw_json.strip()).get("scores", [0.5] * len(new_facts))
                
                # Apply scores to facts
                for i, fact in enumerate(new_facts):
                    fact["importance"] = scores[i] if i < len(scores) else 0.5
            except Exception as e:
                logger.warning(f"Importance scoring failed, using default (0.5): {e}")
                for fact in new_facts: fact["importance"] = 0.5

            # 3. Storage
            await store_facts(user_id, new_facts)
            
            # 4. LEVI v6: Trigger Evolution (Silent Trait Distillation)
            from backend.redis_client import HAS_REDIS
            if HAS_REDIS:
                from backend.redis_client import r as redis_client
                distill_key = f"user:{user_id}:opts:distill_count"
                count = redis_client.incr(distill_key)
                
                if count >= 20: # Every 20 interactions, evolve the persona
                    logger.info(f"[MemoryManager] Triggering silent distillation for {user_id}...")
                    asyncio.create_task(MemoryManager.distill_core_memory(user_id))
                    redis_client.set(distill_key, 0)

            logger.info(f"[MemoryManager] Processed {len(new_facts)} new facts for {user_id}")

        except Exception as e:
            logger.error("process_new_interaction failed for %s: %s", user_id, e)
