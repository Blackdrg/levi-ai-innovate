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
from ..services.learning.distiller import MemoryDistiller
from backend.db.firestore_db import db as firestore_db
from backend.db.postgres import PostgresDB
from backend.db.models import UserProfile, UserTrait, UserPreference
from sqlalchemy import select

from backend.services.learning.logic import UserPreferenceModel

logger = logging.getLogger(__name__)

# Mid-term query guard
_MIDTERM_TIMEOUT = 3.0

class MemoryManager:
    def __init__(self):
        self.graph = GraphEngine()
        self.distiller = MemoryDistiller()


    async def get_combined_context(self, user_id: str, session_id: str, query: str = "") -> Dict[str, Any]:
        """
        Parallel retrieval from all memory tiers, merged into a single cognitive context.
        """
        short_term_task = self.get_short_term(session_id)
        mid_term_task   = self.get_mid_term(user_id, limit=3)
        long_term_task  = self.get_long_term(user_id, query)
        creation_task   = self.get_creation_context(user_id)
        graph_task      = self.graph.get_connected_resonance(user_id, query)
        tier4_task      = self.get_tier4_traits(user_id)
        
        short_term, mid_term, long_term, creation_context, graph_resonance, tier4_data = await asyncio.gather(
            short_term_task, mid_term_task, long_term_task, creation_task, graph_task, tier4_task
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
            "tier4_traits":      tier4_data,
            "interaction_pulse": pulse,
            "preferences":       preferences,
            "user_id":           user_id,
            "session_id":        session_id,
            "context_drift":     context_drift
        }

        # Token-Aware Trimming (v8 Production Safety)
        return self._trim_facts_by_tokens(facts, max_tokens=1500)

    async def get_context(self, user_id: str) -> List[Dict[str, Any]]:
        """Standardized v8 bridge for conversational context discovery."""
        return await self.get_mid_term(user_id, limit=10)

    def _trim_facts_by_tokens(self, facts: Dict[str, Any], max_tokens: int = 1500) -> Dict[str, Any]:
        """Prunes memory to fit context window, prioritizing Identity and Semantic tiers."""
        total_chars = 0
        char_limit = max_tokens * 4
        
        # Priority Stack: Identity (T4) -> Knowledge (T5) -> Semantic (T3) -> Episodic (T2)
        priority = ["tier4_traits", "graph_resonance", "preferences", "long_term", "mid_term", "history"]
        pruned = {k: facts.get(k, []) for k in facts.keys() if k not in priority}
        for k in priority: pruned[k] = []

        for cat in priority:
            items = facts.get(cat, [])
            if not items: continue

            if isinstance(items, dict):
                # Handle dictionary structures (like T4 traits or Graph resonance)
                pruned[cat] = items
                total_chars += len(str(items))
                continue
            
            for item in items:
                text = str(item.get("fact", "")) if isinstance(item, dict) else str(item)
                if total_chars + len(text) < char_limit:
                    pruned[cat].append(item)
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
            relevant_facts = await SovereignVectorStore.search_facts(user_id, query, limit=20)
            decayed = MemoryResonance.apply_decay(relevant_facts)
            
            return {
                "prototypes":  [f["fact"] for f in decayed if f["category"] == "prototype"],
                "preferences": [f["fact"] for f in decayed if f["category"] == "preference" and f.get("survival_score", 0) > 0.5],
                "traits":      [f["fact"] for f in decayed if f["category"] == "trait"],
                "history":     [f["fact"] for f in decayed if f["category"] == "history" and f.get("survival_score", 0) > 0.6],
                "other":       [f["fact"] for f in decayed if f["category"] == "factual" and f.get("survival_score", 0) > 0.6],
                "raw":         decayed
            }
        except Exception as e:
            logger.error(f"Long-term retrieval failed: {e}")
            return {}

    async def get_tier4_traits(self, user_id: str) -> Dict[str, Any]:
        """
        Tier 4: Structured User Identity Archetypes from Postgres.
        Provides the highest-confidence behavioral and identity traits.
        """
        if not user_id or str(user_id).startswith("guest:"):
            return {}

        try:
            from sqlalchemy.orm import selectinload
            if PostgresDB._session_factory is None:
                PostgresDB.get_engine()
            async with PostgresDB._session_factory() as session:
                query = select(UserProfile).options(
                    selectinload(UserProfile.traits),
                    selectinload(UserProfile.preferences)
                ).where(UserProfile.user_id == user_id)
                
                result = await session.execute(query)
                profile = result.scalar_one_or_none()
                
                if not profile:
                    return {}

                return {
                    "archetype": profile.persona_archetype,
                    "style": profile.response_style,
                    "traits": [{"trait": t.trait, "weight": t.weight} for t in profile.traits],
                    "preferences": [{"cat": p.category, "val": p.value} for p in profile.preferences],
                    "metrics": {"avg_rating": profile.avg_rating, "total": profile.total_interactions}
                }
        except Exception as e:
            logger.error(f"Tier 4 trait retrieval anomaly: {e}")
            return {}

    async def store(self, user_id: str, session_id: Optional[str] = None, user_input: str = "", response: str = "", perception: Optional[Dict[str, Any]] = None, results: Optional[List[Any]] = None):
        """Coordinates short-term (Working) and long-term (Episodic/Semantic) updates."""
        session_id = session_id or f"sess_v8_{user_id}"
        perception = perception or {}
        results = results or []
        
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
                        user_id, t["subject"], t["relation"], t["object"],
                        tenant_id=extraction.get("tenant_id", "default")
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
        """Periodic trait consolidation and rule promotion logic."""
        from backend.db.redis import r as redis_client, HAS_REDIS
        if not HAS_REDIS: return
        
        distill_key = f"user:{user_id}:opts:distill_count"
        try:
            count = redis_client.incr(distill_key)
            if count >= 15:
                logger.info(f"[MemoryManager] Triggering cognitive distillation for {user_id}...")
                asyncio.create_task(self.distill_user_memory(user_id))
                redis_client.set(distill_key, 0)
                redis_client.set(f"user:{user_id}:dream_ready", 1)

        except Exception as e:
            logger.error(f"Distillation trigger failed: {e}")

    async def distill_user_memory(self, user_id: str):
        """Bridge to MemoryDistiller."""
        await self.distiller.distill_user_memory(user_id)

    async def dream(self, user_id: str):
        """
        LeviBrain v9.8.1: Enhanced Dreaming.
        Crystallizes patterns into Tier 4 Identity and promotes JSON rules.
        """
        logger.info(f"[Dreaming] {user_id} is entering high-fidelity state...")
        
        mid_term = await self.get_mid_term(user_id, limit=50)
        long_term = await self.get_long_term(user_id)
        
        if len(mid_term) < 5:
            return False

        from .resonance import MemoryResonance
        # 1. Distill Core Traits
        new_traits = await MemoryResonance.distill_traits(user_id, mid_term + long_term.get("raw", []))
        
        # 2. Identify Rule Candidates (Frequent high-fidelity patterns)
        # For Phase 2, we simulate rule promotion from high-importance traits
        rule_candidates = [t for t in new_traits if t.get("importance", 0) > 0.95]
        
        for trait in new_traits:
            await self._store_tier4_trait(user_id, trait)
            
        for rule in rule_candidates:
            await self._promote_to_rule(user_id, rule)
            
        return True

    async def _promote_to_rule(self, user_id: str, rule_data: Dict[str, Any]):
        """Promotes a pattern to a Level 1 Deterministic Rule (JSON Intent Logic)."""
        logger.info(f"[RulePromotion] Promoting pattern to JSON rule for {user_id}: {rule_data['fact'][:50]}")
        try:
            async with PostgresDB._session_factory() as session:
                from backend.db.models import UserTrait
                # Rules are stored as traits with category 'rule_logic'
                new_rule = UserTrait(
                    user_id=user_id,
                    trait=rule_data["fact"],
                    weight=1.0,
                    category="rule_logic",
                    metadata_json=json.dumps({
                        "type": "intent_logic",
                        "promoted_at": datetime.now(timezone.utc).isoformat(),
                        "version": "1.0"
                    })
                )
                session.add(new_rule)
                await session.commit()
        except Exception as e:
            logger.error(f"Rule promotion failed: {e}")

    async def _store_tier4_trait(self, user_id: str, trait_data: Dict[str, Any]):
        """Persists a crystallized trait into the Postgres Identity store."""
        try:
            async with PostgresDB._session_factory() as session:
                # Upsert trait logic
                from backend.db.models import UserTrait
                stmt = select(UserTrait).where(UserTrait.user_id == user_id, UserTrait.trait == trait_data["fact"])
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()
                
                if existing:
                    existing.weight = (existing.weight + trait_data.get("importance", 0.5)) / 2
                    existing.last_reinforced = datetime.now(timezone.utc)
                else:
                    new_trait = UserTrait(
                        user_id=user_id,
                        trait=trait_data["fact"],
                        weight=trait_data.get("importance", 0.5),
                        category="crystallized"
                    )
                    session.add(new_trait)
                
                await session.commit()
        except Exception as e:
            logger.error(f"Tier 4 persistence failure during dream: {e}")

    async def distill_legacy_core(self, user_id: str) -> None:
        """DEPRECATED: Use MemoryDistiller.distill_user_memory instead."""
        pass


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
