"""
backend/core/memory_manager.py

Sovereign Memory Engine v8: 4-Tier Cognitive Memory System.

Tier 1 — Working   (Redis)     : Instant session focus (20 message window)
Tier 2 — Episodic  (Firestore) : Recent session summaries and event clusters
Tier 3 — Semantic  (FAISS/DB)  : Extracted facts and knowledge, vector-searched
Tier 4 — Identity  (Permanent) : Core user personality, values, and traits

Includes:
- Memory Decay (Importance vs Time) via MemoryResonance
- Token-Aware Trimming for context window safety
- Autonomous Evolutionary Distillation (Fact to Trait conversion)
- Real-time Kafka event emission for cognitive telemetry
"""

import logging
import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.db.redis import r as redis_client, HAS_REDIS
from backend.db.firestore_db import db as firestore_db
from backend.services.learning.logic import UserPreferenceModel
from backend.api.v8.telemetry import broadcast_mission_event

# Internal v8 Cognitive Modules
from backend.memory.cache import MemoryCache
from backend.memory.vector_store import SovereignVectorStore
from backend.memory.resonance import MemoryResonance

logger = logging.getLogger(__name__)

# Configurable constants for v8 tuning
_MIDTERM_TIMEOUT = 3.0
_MAX_CONTEXT_TOKENS = 2000

class MemoryManager:
    """
    Sovereign AI Memory Orchestrator v8.
    Manages the lifecycle of cognitive context across 4 distinct tiers.
    """

    # ── Tier 1/2: Short-term & Episodic Retrieval ───────────────────────────

    async def get_short_term(self, session_id: str) -> List[Dict[str, Any]]:
        """Instant session focus from Redis pulse buffer."""
        return await asyncio.to_thread(MemoryCache.get_session_history, session_id)

    async def get_mid_term(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Recent interaction history pulse from Firestore with Redis caching."""
        if not user_id: return []
        
        cache_key = f"mid_term:{user_id}:{limit}"
        cached = MemoryCache.get_cached_context(cache_key)
        if cached: return cached

        try:
            def _fetch():
                docs = (
                    firestore_db.collection("conversations")
                    .where("user_id", "==", user_id)
                    .order_by("updated_at", direction="DESCENDING")
                    .limit(limit)
                    .get()
                )
                return [doc.to_dict() for doc in docs]

            data = await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=_MIDTERM_TIMEOUT)
            MemoryCache.set_cached_context(cache_key, data, ttl=600)
            return data
        except Exception as e:
            logger.error(f"[MemoryV8] Mid-term retrieval failed: {e}")
            return []

    # ── Tier 3/4: Semantic & Identity Retrieval ──────────────────────────────

    async def get_long_term(self, user_id: str, query: str = "") -> Dict[str, Any]:
        """Categorized semantic facts from vector store with resonant decay logic."""
        if not user_id: return {}
        
        try:
            # 1. Semantic Vector Search
            relevant_facts = await SovereignVectorStore.search_facts(user_id, query, limit=15)
            
            # 2. Resonance Decay Application
            decayed = MemoryResonance.apply_decay(relevant_facts)
            
            # 3. Cognitive Categorization
            return {
                "preferences": [f["fact"] for f in decayed if f["category"] == "preference" and f.get("survival_score", 0) > 0.5],
                "traits":      [f["fact"] for f in decayed if f["category"] == "trait"],
                "history":     [f["fact"] for f in decayed if f["category"] == "history" and f.get("survival_score", 0) > 0.6],
                "other":       [f["fact"] for f in decayed if f["category"] == "factual" and f.get("survival_score", 0) > 0.6],
                "raw":         decayed
            }
        except Exception as e:
            logger.error(f"[MemoryV8] Long-term retrieval failed: {e}")
            return {}

    # ── Orchestration: Combined Context ─────────────────────────────────────

    async def get_combined_context(self, user_id: str, session_id: str, query: str = "") -> Dict[str, Any]:
        """
        Parallel retrieval and merging of all memory tiers.
        Includes drift detection and token-aware pruning.
        """
        start_time = asyncio.get_event_loop().time()
        
        # 1. Parallel Neural Retrieval
        tasks = [
            self.get_short_term(session_id),
            self.get_mid_term(user_id, limit=3),
            self.get_long_term(user_id, query),
            self._get_creation_context(user_id)
        ]
        
        short_term, mid_term, long_term, creation_context = await asyncio.gather(*tasks)

        # 2. Preference Sync
        pref_model = UserPreferenceModel(user_id)
        preferences = await pref_model.get_profile()
        moods = [m.get("mood", "philosophical") for m in mid_term if m.get("mood")]
        pulse = moods[0] if moods else preferences.get("preferred_moods", ["philosophical"])[0]

        # 3. Context Drift & Quality Analysis
        context_drift = False
        if len(short_term) > 1:
            recent_inputs = [m.get("user", "") for m in short_term[-3:]]
            if len(query.split()) < 3 and len(recent_inputs) > 0:
                context_drift = True

        facts = {
            "history":           short_term,
            "long_term":         long_term,
            "mid_term":          mid_term,
            "creation_context":  creation_context,
            "interaction_pulse": pulse,
            "preferences":       preferences,
            "traits":            long_term.get("traits", []),
            "user_id":           user_id,
            "session_id":        session_id,
            "context_drift":     context_drift,
            "latency":           int((asyncio.get_event_loop().time() - start_time) * 1000)
        }

        # 4. Token-Aware Pruning for Production Safety
        pruned_context = self._trim_facts_by_tokens(facts, max_tokens=_MAX_CONTEXT_TOKENS)
        
        # 5. Telemetry Pulse
        broadcast_mission_event(user_id, "memory_context_generated", {
            "request_id": session_id, 
            "latency_ms": facts["latency"]
        })

        return pruned_context

    def _trim_facts_by_tokens(self, facts: Dict[str, Any], max_tokens: int) -> Dict[str, Any]:
        """Intelligently prunes history and semantic tiers to fit LLM window."""
        total_chars = 0
        char_limit = max_tokens * 4
        
        # Priority mapping (Identity -> Semantic -> Episodic -> Working)
        priority_tiers = ["traits", "preferences", "long_term", "mid_term", "history"]
        pruned = {k: facts.get(k, []) for k in facts.keys() if k not in priority_tiers}
        for k in priority_tiers: pruned[k] = []

        for tier in priority_tiers:
            items = facts.get(tier, [])
            if tier == "long_term" and isinstance(items, dict):
                items = items.get("raw", [])
            
            for item in items:
                text = str(item.get("fact", "")) if isinstance(item, dict) else str(item)
                if total_chars + len(text) < char_limit:
                    pruned[tier].append(item)
                    total_chars += len(text)
                else: break
        return pruned

    # ── Persistence & Evolutionary Storage ───────────────────────────────────

    async def store(self, user_id: str, session_id: str, user_input: str, response: str, perception: Dict[str, Any], results: List[Any]):
        """Standard interaction persistence entry point."""
        logger.info(f"[MemoryV8] Storing mission results for {session_id}")
        
        # 1. Tier 1 Update (Working Pulse)
        await self._store_working_memory(user_id, session_id, user_input, response)
        
        # 2. Tier 3/4 Extraction (Semantic & Evolution)
        if user_id and not str(user_id).startswith("guest:"):
            if len(user_input.split()) > 4 or len(results) > 1:
                asyncio.create_task(self._process_fact_extraction(user_id, user_input, response))

    async def _store_working_memory(self, user_id: str, session_id: str, user_input: str, bot_response: str):
        """Updates the Redis session buffer."""
        history = await self.get_short_term(session_id)
        history.append({
            "user": user_input,
            "bot": bot_response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if len(history) > 20: history = history[-20:]
        await asyncio.to_thread(MemoryCache.save_session_history, session_id, history, user_id=user_id)

    async def _process_fact_extraction(self, user_id: str, user_input: str, bot_response: str):
        """Analyzes interaction for atomic facts and triggers trait distillation."""
        from backend.core.memory_utils import extract_facts 
        from backend.core.planner import call_lightweight_llm

        try:
            # 1. Extraction via Cognitive Task
            new_facts = await extract_facts(user_input, bot_response)
            if not new_facts: return

            # 2. Importance Scoring Pulse
            scoring_prompt = (
                "Grade these user facts (0.0 to 1.0) on permanent significance.\n"
                f"Facts: {json.dumps([f['fact'] for f in new_facts])}\n"
                "JSON format: {\"scores\": [...]}"
            )
            raw_scores = await call_lightweight_llm([{"role": "system", "content": scoring_prompt}])
            scores = json.loads(raw_scores.strip()).get("scores", [0.5] * len(new_facts))

            # 3. Synchronous Vector Storage
            for i, fact in enumerate(new_facts):
                importance = scores[i] if i < len(scores) else 0.5
                await SovereignVectorStore.store_fact(user_id, fact["fact"], category=fact["category"], importance=importance)

            # 4. Trigger Autonomous Evolution (Fact -> Trait)
            await self._trigger_evolution(user_id)
            
            # 5. Telemetry Pulse
            broadcast_mission_event(user_id, "facts_extracted", {
                "count": len(new_facts)
            })
            
        except Exception as e:
            logger.error(f"[MemoryV8] Fact extraction anomaly: {e}")

    async def _trigger_evolution(self, user_id: str):
        """Manages interaction thresholds for trait distillation."""
        if not HAS_REDIS: return
        
        distill_key = f"user:{user_id}:opts:distill_count"
        try:
            count = redis_client.incr(distill_key)
            if count >= 20: 
                logger.info(f"[MemoryV8] Triggering evolutionary trait distillation for {user_id}")
                asyncio.create_task(self.distill_core_memory(user_id))
                redis_client.set(distill_key, 0)
        except Exception: pass

    async def distill_core_memory(self, user_id: str) -> None:
        """Consolidates fragmented Tier 3 points into high-level Tier 4 traits."""
        from backend.core.memory_utils import store_facts
        from backend.core.planner import call_lightweight_llm

        try:
            # 1. Gather semantic fragments
            facts_data = await SovereignVectorStore.search_facts(user_id, query="personality and values", limit=25)
            if len(facts_data) < 10: return

            # 2. Strategic Distillation Pass
            fact_strings = "\n".join([f"- {f.get('fact')} (Importance: {f.get('importance', 0.5)})" for f in facts_data])
            prompt = (
                "You are the LEVI Core Distiller. Distill these fragmented facts into 3-5 deep core traits.\n"
                f"Material:\n{fact_strings}\n\n"
                "JSON format: {\"distilled_traits\": [{\"fact\": \"...\", \"importance\": 0.95}]}"
            )

            raw_json = await call_lightweight_llm([{"role": "system", "content": prompt}])
            if "```json" in raw_json: raw_json = raw_json.split("```json")[1].split("```")[0]
            
            data = json.loads(raw_json.strip())
            new_traits = data.get("distilled_traits", [])
            
            if new_traits:
                for trait in new_traits: trait["category"] = "trait"
                await store_facts(user_id, new_traits)
                logger.info(f"[MemoryV8] Evolution Complete: Consolidated {len(facts_data)} facts into {len(new_traits)} traits.")

        except Exception as e:
            logger.error(f"[MemoryV8] Distillation failure: {e}")

    # ── Utilities ────────────────────────────────────────────────────────────

    async def _get_creation_context(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch recent Studio/Gallery activity with cache synchronization."""
        if not user_id or str(user_id).startswith("guest:"): return []
        
        cache_key = f"creation_ctx:{user_id}"
        cached = MemoryCache.get_cached_context(cache_key)
        if cached: return cached

        try:
            def _fetch():
                jobs = firestore_db.collection("jobs") \
                    .where("user_id", "==", user_id) \
                    .where("status", "==", "completed") \
                    .order_by("completed_at", direction="DESCENDING") \
                    .limit(3).get()
                
                return [{
                    "service": "studio", "type": d.get("type"), "prompt": d.get("prompt"), "url": d.get("result_url")
                } for doc in jobs if (d := doc.to_dict())]

            creations = await asyncio.to_thread(_fetch)
            MemoryCache.set_cached_context(cache_key, creations, ttl=900)
            return creations
        except Exception: return []

    async def clear_all_user_data(self, user_id: str) -> int:
        """Hardened absolute memory wipe for privacy/compliance."""
        logger.warning(f"SOVEREIGN WIPE: Purging all cognitive data for {user_id}")
        
        # 1. Vector Purge (Tier 3/4)
        await SovereignVectorStore.clear_user_memory(user_id)
        
        # 2. Firestore Fact Purge (Tier 2/3)
        def _purge_firestore():
            batch = firestore_db.batch()
            docs = firestore_db.collection("user_facts").where("user_id", "==", user_id).limit(500).get()
            count = 0
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
            if count > 0: batch.commit()
            return count

        cleared_count = await asyncio.to_thread(_purge_firestore)

        # 3. Redis Cache Purge (Tier 1)
        if HAS_REDIS:
            try:
                keys = redis_client.keys(f"*:{user_id}*")
                if keys: redis_client.delete(*keys)
                redis_client.delete(f"chat:{user_id}:history")
            except Exception as e:
                logger.error(f"Redis purge failed: {e}")

        # 4. Mission Telemetry
        broadcast_mission_event(user_id, "memory_wipe_complete", {
            "facts_cleared": cleared_count
        })

        return cleared_count
