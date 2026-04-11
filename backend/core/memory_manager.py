"""
backend/core/memory_manager.py

Sovereign Memory Engine v14: 4-Tier Cognitive Memory System.

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
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.utils.runtime_tasks import create_tracked_task

from backend.db.redis import r as redis_client, HAS_REDIS
from backend.db.postgres import PostgresDB
from backend.db.models import Mission, Message, UserFact, UserProfile, UserTrait, UserPreference, MissionMetric, CreationJob
from backend.services.learning.logic import UserPreferenceModel
from backend.api.telemetry import broadcast_mission_event


# Internal v8 Cognitive Modules
from backend.memory.cache import MemoryCache
from backend.memory.vector_store import SovereignVectorStore
from backend.memory.resonance import MemoryResonance
from backend.db.neo4j_client import Neo4jClient
from backend.memory.bm25_retriever import BM25Retriever

logger = logging.getLogger(__name__)

# Configurable constants for v8 tuning
_MIDTERM_TIMEOUT = 3.0
_MAX_CONTEXT_TOKENS = 2000

class MemoryManager:
    """
    Sovereign AI Memory Orchestrator v14.
    Manages the lifecycle of cognitive context across 4 distinct tiers.
    """

    async def initialize(self) -> None:
        """Initialize memory tiers and connections."""
        logger.info("[MemoryV8] Initializing Sovereign Memory Engine tiers...")
        from backend.services.mcm import mcm_service
        await mcm_service.start()
        
        # Start background maintenance tasks
        create_tracked_task(self._background_reindexing_loop(), name="memory-reindexing-loop")

    async def shutdown(self) -> None:
        """Graceful teardown of memory tiers."""
        logger.info("[MemoryV8] Shutting down memory tiers...")
        from backend.services.mcm import mcm_service
        await mcm_service.stop()


    # ── Tier 1/2: Short-term & Episodic Retrieval ───────────────────────────

    async def get_short_term(self, session_id: str) -> List[Dict[str, Any]]:
        """Instant session focus from Redis pulse buffer."""
        return await asyncio.to_thread(MemoryCache.get_session_history, session_id)

    async def get_mid_term(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Recent interaction history pulse from Postgres with Redis caching."""
        if not user_id: return []
        
        cache_key = f"mid_term:{user_id}:{limit}"
        cached = MemoryCache.get_cached_context(cache_key)
        if cached: return cached

        try:
            from sqlalchemy import select
            async with PostgresDB._session_factory() as session:
                stmt = select(Mission).where(Mission.user_id == user_id).order_by(Mission.updated_at.desc()).limit(limit)
                result = await session.execute(stmt)
                missions = result.scalars().all()
                data = [
                    {
                        "mission_id": m.mission_id,
                        "objective": m.objective,
                        "status": m.status,
                        "updated_at": m.updated_at.isoformat()
                    } for m in missions
                ]
            
            MemoryCache.set_cached_context(cache_key, data, ttl=600)
            return data
        except Exception as e:
            logger.error(f"[MemoryV8] Mid-term retrieval failed: {e}")
            return []

    # ── Tier 3/4: Semantic & Identity Retrieval ──────────────────────────────

    async def get_long_term(self, user_id: str, query: str = "") -> Dict[str, Any]:
        """Hybrid retrieval: Categorized semantic facts (FAISS) + Keyword (BM25) + Graph (Neo4j)."""
        if not user_id: return {}
        
        try:
            # 1. Semantic Vector Search (FAISS)
            vector_facts = await SovereignVectorStore.search_facts(user_id, query, limit=15)
            
            # 2. Keyword Search (BM25)
            # Re-rank local vectors using BM25 for keyword precision
            bm25 = BM25Retriever()
            keyword_facts = bm25.compute_bm25_scores(query, vector_facts)
            
            # 3. Graph Resonance (Neo4j)
            graph_resonance = await Neo4jClient.get_resonance_entities(user_id, query)
            
            # 4. Resonance Decay Application (v14.0 4-Factor)
            decayed = MemoryResonance.apply_decay(keyword_facts)
            
            # 5. Hybrid Merge & Cognitive Categorization
            return {
                "preferences": [f["fact"] for f in decayed if f["category"] == "preference" and f.get("survival_score", 0) > 0.5],
                "traits":      [f["fact"] for f in decayed if f["category"] == "trait"],
                "history":     [f["fact"] for f in decayed if f["category"] == "history" and f.get("survival_score", 0) > 0.6],
                "graph_resonance": graph_resonance,
                "raw":         decayed
            }
        except Exception as e:
            logger.error(f"[MemoryV8] Hybrid long-term retrieval failed: {e}")
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
            "identity_insights": [f["fact"] for f in long_term.get("raw", []) if f.get("category") == "insight"],
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

    async def store(self, user_id: str, session_id: str, user_input: str, response: str, perception: Dict[str, Any], results: List[Any], fidelity: Optional[float] = None):
        """Standard interaction persistence entry point."""
        logger.info(f"[MemoryV8] Storing mission results for {session_id}")
        
        # 1. Tier 1 Update (Working Pulse)
        await self._store_working_memory(user_id, session_id, user_input, response)
        
        # 2. Emit Consistency Event (Redis Stream)
        from backend.services.mcm import mcm_service
        await mcm_service.emit_event("interaction", user_id, session_id, {
            "input": user_input,
            "response": response,
            "fidelity": fidelity
        })

        
        # 2. Tier 3/4 Extraction (Semantic & Evolution)
        if user_id and not str(user_id).startswith("guest:"):
            if len(user_input.split()) > 4 or len(results) > 1:
                create_tracked_task(self._process_fact_extraction(user_id, user_input, response), name="fact_extraction")
        
        # 3. Learning Loop Crystallization (v14.0.0-Autonomous-SOVEREIGN)
        if fidelity:
            from backend.core.learning_loop import LearningLoop
            create_tracked_task(LearningLoop.crystallize_pattern(session_id, user_input, response, fidelity), name="learning_crystallize")

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
            
            # 5. Telemetry Pulse & MCM Broadcast (Graduation #6)
            broadcast_mission_event(user_id, "facts_extracted", {
                "count": len(new_facts)
            })
            
            from backend.services.mcm import mcm_service
            await mcm_service.emit_event("fact_extracted", user_id, "background_extraction", {
                "facts": new_facts,
                "count": len(new_facts),
                "timestamp": time.time()
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
                create_tracked_task(self.distill_core_memory(user_id), name="distill_core_memory")
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
                
                # Global MCM Pulse (Graduation #6)
                from backend.services.mcm import mcm_service
                for trait in new_traits:
                    await mcm_service.emit_event("trait_distilled", user_id, "evolution_cycle", {
                        "trait": trait.get("fact"),
                        "importance": trait.get("importance", 0.95),
                        "timestamp": time.time()
                    })

                logger.info(f"[MemoryV8] Evolution Complete: Consolidated {len(facts_data)} facts into {len(new_traits)} traits.")

        except Exception as e:
            logger.error(f"[MemoryV8] Distillation failure: {e}")

    async def _background_reindexing_loop(self):
        """Cyclical background maintenance: Re-indexes memory for active users."""
        logger.info("[MemoryV8] Background maintenance loop: [ACTIVE]")
        while True:
            try:
                # Wait for 4 hours between full cycles
                await asyncio.sleep(4 * 3600) 
                
                logger.info("[MemoryV8] Starting cyclical memory re-indexing pass...")
                from sqlalchemy import select
                async with PostgresDB._session_factory() as session:
                    # Identify 'active' users as those with recent missions
                    stmt = select(Mission.user_id).distinct().order_by(Mission.updated_at.desc()).limit(100)
                    result = await session.execute(stmt)
                    active_users = result.scalars().all()
                    
                for user_id in active_users:
                    if user_id and not str(user_id).startswith("guest:"):
                        await SovereignVectorStore.reindex_user_memory(user_id)
                        # Yield to other tasks
                        await asyncio.sleep(1)
                
                logger.info(f"[MemoryV8] Cyclical re-indexing complete for {len(active_users)} users.")
            except Exception as e:
                logger.error(f"[MemoryV8] Background maintenance error: {e}")
                await asyncio.sleep(600)

    # ── Utilities ────────────────────────────────────────────────────────────

    async def _get_creation_context(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch recent CreationJob activity from Postgres (Zero-Cloud)."""
        if not user_id or str(user_id).startswith("guest:"): return []
        
        cache_key = f"creation_ctx:{user_id}"
        cached = MemoryCache.get_cached_context(cache_key)
        if cached: return cached

        try:
            from sqlalchemy import select
            async with PostgresDB._session_factory() as session:
                stmt = select(CreationJob).where(
                    CreationJob.user_id == user_id,
                    CreationJob.status == "completed"
                ).order_by(CreationJob.completed_at.desc()).limit(3)
                
                result = await session.execute(stmt)
                jobs = result.scalars().all()
                
                creations = [{
                    "service": "studio", 
                    "type": "asset", 
                    "prompt": j.objective, 
                    "url": j.result_url
                } for j in jobs]
                
                MemoryCache.set_cached_context(cache_key, creations, ttl=900)
                return creations
        except Exception as e: 
            logger.error(f"[MemoryV8] Creation context retrieval failed: {e}")
            return []

    async def clear_all_user_data(self, user_id: str) -> int:
        """Hardened absolute memory wipe for privacy/compliance (GDPR)."""
        logger.warning(f"SOVEREIGN WIPE: Purging all cognitive data for {user_id}")
        
        # 1. Vector Purge (Tier 4: HNSW / Tier 3: BM25)
        await SovereignVectorStore.clear_user_memory(user_id)
        
        # 2. Postgres Absolute SQL Purge (Tiers 2, 3, 4)
        from sqlalchemy import delete
        cleared_count = 0
        
        try:
            async with PostgresDB._session_factory() as session:
                async with session.begin():
                    # Order matters for foreign keys
                    # Wipe Tier 3: Learned Facts
                    res = await session.execute(delete(UserFact).where(UserFact.user_id == user_id))
                    cleared_count += res.rowcount
                    
                    # Wipe Tier 2: Episodic (Missions & Messages)
                    # Need to subquery for mission_messages if not cascade delete at DB level
                    mission_ids_stmt = select(Mission.mission_id).where(Mission.user_id == user_id)
                    mission_ids_res = await session.execute(mission_ids_stmt)
                    mission_ids = mission_ids_res.scalars().all()
                    
                    if mission_ids:
                        await session.execute(delete(Message).where(Message.mission_id.in_(mission_ids)))
                    
                    await session.execute(delete(Mission).where(Mission.user_id == user_id))
                    
                    # Wipe Tier 4: Identity (Traits, Preferences, Profile)
                    await session.execute(delete(UserTrait).where(UserTrait.user_id == user_id))
                    await session.execute(delete(UserPreference).where(UserPreference.user_id == user_id))
                    await session.execute(delete(MissionMetric).where(MissionMetric.user_id == user_id))
                    await session.execute(delete(CreationJob).where(CreationJob.user_id == user_id))
                    await session.execute(delete(UserProfile).where(UserProfile.user_id == user_id))
                    
                await session.commit()
            logger.info(f"[Postgres] Absolute SQL resonance purge complete for user: {user_id}")
        except Exception as e:
            logger.error(f"Postgres purge failed for {user_id}: {e}")

        # 3. Neo4j Graph Purge (Relationships & Nodes)
        try:
            await Neo4jClient.clear_user_data(user_id)
        except Exception as e:
            logger.error(f"Neo4j purge failed for {user_id}: {e}")

        # 4. Redis Cache Purge (Tier 1)
        if HAS_REDIS:
            try:
                keys = redis_client.keys(f"*:{user_id}*")
                if keys: redis_client.delete(*keys)
                redis_client.delete(f"chat:{user_id}:history")
            except Exception as e:
                logger.error(f"Redis purge failed: {e}")

        # 5. Global MCM Pulse (Tier 5)
        try:
            from backend.services.mcm import mcm_service
            await mcm_service.emit_event("PURGE_USER", user_id, "compliance_wipe", {"timestamp": time.time()})
            logger.info(f"[MCM] Broadcasted PURGE_USER pulse for {user_id}")
        except Exception as e:
            logger.error(f"[MCM] Global purge pulse failed: {e}")

        # 6. Mission Telemetry
        broadcast_mission_event(user_id, "memory_wipe_complete", {
            "facts_cleared": cleared_count
        })

        return cleared_count
