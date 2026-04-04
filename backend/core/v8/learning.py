import logging
import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from backend.api.v8.telemetry import broadcast_mission_event
from backend.memory.cache import MemoryCache
from backend.memory.vector_store import SovereignVectorStore
from backend.core.v8.critic import ReflectionEngine

logger = logging.getLogger(__name__)

class FragilityTracker:
    """
    Sovereign v8.7: Dynamic Fragility Tracking.
    Monitors engine performance and calculates self-optimization weights.
    """
    
    @staticmethod
    def get_fragility(user_id: str, domain: str) -> float:
        """
        Returns a fragility score (0.0 to 1.0) for a specific cognitive domain.
        Higher fragility = more rigorous self-reflection.
        """
        cache_key = f"fragility:{user_id}:{domain}"
        data = MemoryCache.get_cached_context(cache_key) or {"failures": 0, "last_failure": None, "success_streak": 0}
        
        # Moderate Decay: Relax after 3-5 successes or 30 minutes
        if data.get("last_failure"):
            last_fail = datetime.fromisoformat(data["last_failure"])
            if (datetime.now(timezone.utc) - last_fail) > timedelta(minutes=30):
                return 0.0
        
        failures = data.get("failures", 0)
        streak = data.get("success_streak", 0)
        
        # Moderate decay factor: relax fragility as success streak grows
        if streak >= 3:
            return 0.0
            
        return min(1.0, failures * 0.4)

    @staticmethod
    def record_outcome(user_id: str, domain: str, success: bool):
        """Updates the fragility index for a domain based on mission outcome."""
        cache_key = f"fragility:{user_id}:{domain}"
        data = MemoryCache.get_cached_context(cache_key) or {"failures": 0, "last_failure": None, "success_streak": 0}
        
        if success:
            data["success_streak"] = data.get("success_streak", 0) + 1
            if data["success_streak"] >= 3:
                data["failures"] = 0 # Reset on moderate streak
        else:
            data["failures"] = data.get("failures", 0) + 1
            data["last_failure"] = datetime.now(timezone.utc).isoformat()
            data["success_streak"] = 0
            
        MemoryCache.set_cached_context(cache_key, data, ttl=3600)

class PatternRegistry:
    """
    LeviBrain v8.8: Exact-Match Pattern Registry.
    Tracks repeated LLM reasoning patterns to promote them to deterministic rules.
    """
    
    @staticmethod
    def track_pattern(user_id: str, query: str, response: str) -> bool:
        """
        Increments hit count for a query/response pair.
        Returns True if promoted to a deterministic rule (hits >= 3).
        """
        cache_key = f"pattern_hits:{hash(query)}"
        data = MemoryCache.get_cached_context(cache_key) or {"query": query, "response": response, "hits": 0}
        
        if data["response"] == response:
            data["hits"] += 1
            MemoryCache.set_cached_context(cache_key, data, ttl=86400 * 7) # Keep for 7 days
            
            if data["hits"] >= 3:
                logger.info(f"[PatternRegistry] Promoting pattern to deterministic rule: {query[:50]}...")
                return True
        else:
            # Response diverged, reset or track alternative? 
            # For now, strict exact match means same response must be returned.
            data["response"] = response
            data["hits"] = 1
            MemoryCache.set_cached_context(cache_key, data, ttl=86400 * 7)
            
        return False

class CrystallizationEngine:
    """
    Sovereign v8.7: Knowledge Crystallization.
    Transforms high-fidelity reasoning patterns into reusable prototypes.
    """
    
    @staticmethod
    async def crystallize_prototype(user_id: str, mission_data: Dict[str, Any]):
        """Distills a successful mission into a Reasoning Prototype."""
        # Only crystallize exceptionally successful missions (Fidelity > 0.95)
        fidelity = mission_data.get("fidelity_score", 0.0)
        if fidelity < 0.95: return
        
        proto_id = f"proto_{uuid.uuid4().hex[:6]}"
        logger.info(f"[Crystallization] Distilling reasoning prototype: {proto_id}")
        
        prototype = {
            "id": proto_id,
            "intent": mission_data.get("intent", "general"),
            "style": mission_data.get("style", "analytical"),
            "pattern": mission_data.get("methodology", "N/A"),
            "input_context": mission_data.get("input_signature", ""),
            "crystallized_at": datetime.now(timezone.utc).isoformat(),
            "fidelity": fidelity
        }
        
        # Store in Identity Tier (Category: prototype)
        fact_text = f"Reasoning Prototype [{prototype['intent']}]: {prototype['pattern'][:200]}"
        await SovereignVectorStore.store_fact(
            user_id, 
            fact_text, 
            category="prototype", 
            importance=0.9
        )
        
        # v8.14: Distill into Knowledge Graph (Neo4j Bridge)
        try:
             from backend.utils.vector_db import add_to_knowledge_graph
             await add_to_knowledge_graph(user_id, prototype["intent"], "HAS_PROTOTYPE", prototype["id"], metadata=prototype)
        except Exception as e:
             logger.warning(f"[Crystallization] Knowledge Graph distillation failed: {e}")

        broadcast_mission_event(user_id, "intelligence_crystallized", prototype)

from .rules_engine import RulesEngine

class LearningLoopV8:
    """
    LeviBrain v8.12: Evolutionary Intelligence Loop.
    Autonomous strategic adjustment based on environmental outcomes.
    """
    
    _rules_engine = RulesEngine()

    @classmethod
    async def process_mission_outcome(cls, user_id: str, outcome: Dict[str, Any]):
        """
        The central heart of the evolutionary loop (v8.12).
        Updates fragility and triggers crystallization.
        """
        intent = outcome.get("intent", "general")
        success = outcome.get("total_score", 0.0) >= 0.8 if "total_score" in outcome else True
        level = outcome.get("level", 4)
        
        # 1. Update Domain Fragility (Self-Optimization Weighting)
        FragilityTracker.record_outcome(user_id, intent, success)
        
        # 2. EXACT-MATCH LEARNING RULE (v8.14 Hardened)
        if level >= 2 and success:
            query = outcome.get("query")
            response = outcome.get("response")
            
            # Track recurring patterns for promotion to Rules Engine
            if PatternRegistry.track_pattern(user_id, query, response):
                
                # v8.14: Validation Pass via ReflectionEngine before promotion
                reflection = ReflectionEngine()
                # Mocking a goal for the reflection pass
                class MockGoal: objective = "Validate deterministic rule." ; success_criteria = ["No hallucination", "Logical correctness"] ; self_correction_weight = 0.9
                
                eval_res = await reflection.evaluate(response, MockGoal(), {"input": query})
                
                if eval_res["is_satisfactory"]:
                    # Promote to persistent Rules Engine
                    cls._rules_engine.create_rule(query, response)
                    broadcast_mission_event(user_id, "rule_promoted", {"query": query, "fidelity": eval_res["score"]})
                else:
                    logger.warning(f"[V8 Evolution] Rule promotion rejected by Critic: {query[:50]}")
                    broadcast_mission_event(user_id, "rule_rejected", {"query": query, "reason": eval_res["issues"]})

        # 3. Trigger Crystallization (Skill Acquisition - Prototype Layer)
        if success and outcome.get("total_score", 0.0) >= 0.95:
            await CrystallizationEngine.crystallize_prototype(user_id, outcome)
            
        # 4. Archive Failures for Cluster Analysis
        if not success:
            logger.warning(f"[V8 Evolution] Fragile pattern detected in domain: {intent}")
            broadcast_mission_event(user_id, "evolution_fragility", {
                "domain": intent,
                "reason": outcome.get("issues", "Logic Divergence"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

    @classmethod
    async def apply_importance_decay(cls, memory_vault: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Maintains cognitive efficiency via resonance-based decay."""
        now = datetime.now(timezone.utc)
        survivors = []
        for mem in memory_vault:
            ts = mem.get("timestamp") or mem.get("crystallized_at")
            if not ts: 
                survivors.append(mem)
                continue
            age_days = (now - datetime.fromisoformat(ts)).days
            importance = mem.get("importance", 5)
            resonance = importance / (1 + age_days * 0.1)
            if resonance > 0.5: survivors.append(mem)
        return survivors
