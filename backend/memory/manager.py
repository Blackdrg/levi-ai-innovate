"""
Sovereign Memory Manager v8.
The high-level orchestrator for the 4-Tier Memory System.
Refactored into Autonomous Memory Ecosystem.
"""

import logging
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .cache import MemoryCache
from .vector_store import SovereignVectorStore
from .resonance import MemoryResonance
from .graph_engine import GraphEngine
from backend.db.firestore_db import db as firestore_db
from backend.services.learning.logic import UserPreferenceModel

logger = logging.getLogger(__name__)

# Mid-term query guard
_MIDTERM_TIMEOUT = 3.0

class MemoryManager:
    def __init__(self):
        self.graph = GraphEngine()

    async def get_combined_context(self, user_id: str, session_id: str, query: str = "") -> Dict[str, Any]:
        """
        Parallel retrieval from all memory tiers, merged into a single cognitive context.
        """
        short_term_task = self.get_short_term(session_id)
        mid_term_task   = self.get_mid_term(user_id, limit=3)
        long_term_task  = self.get_long_term(user_id, query)
        creation_task   = self.get_creation_context(user_id)
        graph_task      = self.graph.get_connected_resonance(user_id, query)
        
        short_term, mid_term, long_term, creation_context, graph_resonance = await asyncio.gather(
            short_term_task, mid_term_task, long_term_task, creation_task, graph_task
        )

        # Build preferences pulse
        pref_model = UserPreferenceModel(user_id)
        preferences = await pref_model.get_profile()
        moods = [m.get("mood", "philosophical") for m in mid_term if m.get("mood")]
        pulse = moods[0] if moods else preferences.get("preferred_moods", ["philosophical"])[0]

        # Context Drift Detection (v8 Hardened)
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
            "graph_resonance":   graph_resonance,
            "interaction_pulse": pulse,
            "preferences":       preferences,
            "user_id":           user_id,
            "session_id":        session_id,
            "context_drift":     context_drift
        }

        # Token-Aware Trimming (v8 Production Safety)
        return self._trim_facts_by_tokens(facts, max_tokens=1500)

    def _trim_facts_by_tokens(self, facts: Dict[str, Any], max_tokens: int = 1500) -> Dict[str, Any]:
        """Prunes memory to fit context window, prioritizing Identity and Semantic tiers."""
        total_chars = 0
        char_limit = max_tokens * 4
        
        priority = ["traits", "preferences", "long_term", "mid_term", "history"]
        pruned = {k: facts.get(k, []) for k in facts.keys() if k not in priority}
        for k in priority: pruned[k] = []

        for cat in priority:
            items = facts.get(cat, [])
            if isinstance(items, dict): # Handle long_term dict
                items = items.get("raw", [])
            
            for item in items:
                text = str(item.get("fact", "")) if isinstance(item, dict) else str(item)
                if total_chars + len(text) < char_limit:
                    if cat == "long_term": pruned[cat].append(item)
                    else: pruned[cat].append(item)
                    total_chars += len(text)
                else: break
        return pruned

    async def get_short_term(self, session_id: str) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(MemoryCache.get_session_history, session_id)

    async def get_mid_term(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Async: recent interaction history pulse from Firestore with Redis caching."""
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
            logger.error(f"Mid-term retrieval failed: {e}")
            return []

    async def get_long_term(self, user_id: str, query: str = "") -> Dict[str, Any]:
        """Categorized semantic facts from persistent vector store with decay."""
        if not user_id: return {}
        
        try:
            relevant_facts = await SovereignVectorStore.search_facts(user_id, query, limit=15)
            decayed = MemoryResonance.apply_decay(relevant_facts)
            
            return {
                "preferences": [f["fact"] for f in decayed if f["category"] == "preference" and f.get("survival_score", 0) > 0.5],
                "traits":      [f["fact"] for f in decayed if f["category"] == "trait"],
                "history":     [f["fact"] for f in decayed if f["category"] == "history" and f.get("survival_score", 0) > 0.6],
                "other":       [f["fact"] for f in decayed if f["category"] == "factual" and f.get("survival_score", 0) > 0.6],
                "raw":         decayed
            }
        except Exception as e:
            logger.error(f"Long-term retrieval failed: {e}")
            return {}

    async def store(self, user_id: str, session_id: str, user_input: str, response: str, perception: Dict[str, Any], results: List[Any]):
        """Coordinates short-term (Working) and long-term (Episodic/Semantic) updates."""
        logger.info("[MemoryManager] Storing interaction: %s", session_id)
        
        await self.store_memory(user_id, session_id, user_input, response)
        
        if user_id and not str(user_id).startswith("guest:"):
            if len(user_input.split()) > 4 or len(results) > 1:
                asyncio.create_task(self.process_extraction(user_id, user_input, response))

    async def store_memory(self, user_id: str, session_id: str, user_input: str, bot_response: str):
        history = await self.get_short_term(session_id)
        history.append({
            "user": user_input,
            "bot": bot_response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if len(history) > 20: history = history[-20:]
        await asyncio.to_thread(MemoryCache.save_session_history, session_id, history, user_id=user_id)

    async def process_extraction(self, user_id: str, user_input: str, bot_response: str):
        from backend.core.memory_utils import extract_memory_graph 
        from backend.core.planner import call_lightweight_llm

        try:
            extraction = await extract_memory_graph(user_input, bot_response)
            new_facts = extraction.get("facts", [])
            triplets = extraction.get("triplets", [])
            
            if not new_facts and not triplets: return

            # 1. Store Relational Triplets (Neo4j)
            if triplets:
                for t in triplets:
                    asyncio.create_task(self.graph.upsert_triplet(
                        user_id, t["subject"], t["relation"], t["object"]
                    ))

            # 2. Store Atomic Facts (FAISS/Mongo)
            if new_facts:
                scoring_prompt = (
                    "Grade these user facts (0.0 to 1.0) on permanent identity significance.\n"
                    f"Facts: {json.dumps([f['fact'] for f in new_facts])}\n"
                    "Output JSON: {\"scores\": [...]}"
                )
                raw_scores = await call_lightweight_llm([{"role": "system", "content": scoring_prompt}])
                scores = json.loads(raw_scores.strip()).get("scores", [0.5] * len(new_facts))

                for i, fact in enumerate(new_facts):
                    importance = scores[i] if i < len(scores) else 0.5
                    await SovereignVectorStore.store_fact(user_id, fact["fact"], category=fact["category"], importance=importance)

            # 3. Trigger Evolutionary Distillation
            await self._trigger_distillation(user_id)
            logger.info(f"[MemoryManager] Relational Extraction Complete for {user_id}")
        except Exception as e:
            logger.error(f"Memory extraction anomaly: {e}")

    async def _trigger_distillation(self, user_id: str):
        """Periodic trait consolidation logic using Redis interaction counters."""
        from backend.db.redis import r as redis_client, HAS_REDIS
        if not HAS_REDIS: return
        
        distill_key = f"user:{user_id}:opts:distill_count"
        try:
            count = redis_client.incr(distill_key)
            if count >= 20: 
                logger.info(f"[MemoryManager] Triggering silent distillation for {user_id}...")
                asyncio.create_task(self.distill_core_memory(user_id))
                redis_client.set(distill_key, 0)
        except Exception as e:
            logger.error(f"Distillation trigger failed: {e}")

    async def distill_core_memory(self, user_id: str) -> None:
        """Identifying clusters of fragmented facts and distilling them into unified core traits."""
        from backend.core.memory_utils import store_facts
        from backend.core.planner import call_lightweight_llm

        try:
            # 1. Fetch recent facts to identify patterns
            facts_data = await SovereignVectorStore.search_facts(user_id, query="user personality and values", limit=25)
            if len(facts_data) < 10: return

            fact_strings = "\n".join([f"- {f.get('fact')} (Importance: {f.get('importance', 0.5)})" for f in facts_data])
            
            prompt = (
                "You are the LEVI Core Distiller. Analyze these fragmented user facts and distill them into "
                "3-5 deep, high-level core identity traits or permanent preferences.\n"
                f"Facts:\n{fact_strings}\n\n"
                "Output ONLY JSON: {\"distilled_traits\": [{\"fact\": \"...\", \"importance\": 0.95}]}"
            )

            raw_json = await call_lightweight_llm([{"role": "system", "content": prompt}])
            if "```json" in raw_json: raw_json = raw_json.split("```json")[1].split("```")[0]
            
            data = json.loads(raw_json.strip())
            new_traits = data.get("distilled_traits", [])
            
            if new_traits:
                for trait in new_traits: trait["category"] = "trait"
                await store_facts(user_id, new_traits)
                logger.info(f"[MemoryManager] Consolidate {len(facts_data)} points into {len(new_traits)} traits for {user_id}")

        except Exception as e:
            logger.error(f"Memory distillation failed for {user_id}: {e}")

    async def get_creation_context(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch recent Studio activity with Redis caching."""
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
                    "service": "studio",
                    "type": data.get("type", "image"),
                    "prompt": data.get("prompt", ""),
                    "result": data.get("result_url", ""),
                    "timestamp": data.get("completed_at")
                } for doc in jobs if (data := doc.to_dict())]

            creations = await asyncio.to_thread(_fetch)
            MemoryCache.set_cached_context(cache_key, creations, ttl=900)
            return creations
        except Exception as e:
            logger.warning(f"Creation context retrieval failed for {user_id}: {e}")
            return []

    async def clear_all_user_data(self, user_id: str):
        """Standard v8 absolute memory wipe."""
        logger.warning(f"SOVEREIGN WIPE: Clearing all data for {user_id}")
        # Implementation bridged to Vector store and Database layers
        from .vector_store import SovereignVectorStore
        await SovereignVectorStore.clear_user_memory(user_id)
        # Clear Firestore and Redis logic here...
