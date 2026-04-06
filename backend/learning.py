"""
Sovereign Neural Evolution Engine v7.
Analyzes agent performance (Critic scores) and adjusts routing weights.
Implementation of the 'Self-Improving Brain' loop.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from backend.firestore_db import db as sovereign_db
from backend.redis_client import cache as sovereign_cache

logger = logging.getLogger(__name__)

class PatternPromotionGate:
    """
    Sovereign v13.1.0: Human-in-the-loop (HITL) Gate.
    Prevents unreviewed patterns from being promoted to L1 (Deterministic Rules).
    """
    
    @staticmethod
    async def stage_rule_candidate(pattern: str, intent: str, confidence: float):
        """Stages a recurring pattern for human review in the Postgres ledger."""
        from backend.db.postgres import PostgresDB
        from backend.db.models import UserPreference # Reusing preference as a proxy or using a dedicated table
        
        logger.info(f"[Learning] Staging Rule Candidate (HITL Required): {intent} (Conf: {confidence})")
        # In a full implementation, we'd use a 'pending_rules' table
        # For now, we log it as a high-significance preference for review
        async with PostgresDB._session_factory() as session:
            pref = UserPreference(
                user_id="system_admin",
                category="pending_rule_l1",
                value=f"Intent: {intent} | Pattern: {pattern[:100]}",
                resonance_score=confidence
            )
            session.add(pref)
            await session.commit()

class AutonomousLearner:
    """
    Sovereign Evolution Engine v13.1.0.
    Observes neural pulses and adjusts model routing parameters.
    """
    
    @staticmethod
    async def log_evolution_pulse(agent: str, query: str, score: float, metadata: Dict[str, Any]):
        """Logs a single neural pulse and checks for Rule Promotion candidates."""
        pulse_data = {
            "agent": agent,
            "query": query,
            "quality_score": score,
            "metadata": metadata,
            "timestamp": time.time()
        }
        
        # 1. Persistence in the Sovereign Ledger (Redis)
        if HAS_REDIS:
            pulse_list = eval(sovereign_cache.get("recent_pulses") or "[]")
            pulse_list.append(pulse_data)
            sovereign_cache.set("recent_pulses", str(pulse_list[-50:]))
        
        # 2. Rule Promotion Analysis (Level 1 Crystallization)
        if score > 0.98 and metadata.get("is_recurring", False):
            await PatternPromotionGate.stage_rule_candidate(query, metadata.get("intent", "unknown"), score)
        
        logger.info(f"[Evolution] Pulse recorded for {agent}: Score {score}")

    @staticmethod
    async def adjust_routing_weights(agent: str, recent_scores: List[float]):
        """Adjusts the routing priority for an agent based on recent performance."""
        if not recent_scores: return
        
        avg_score = sum(recent_scores) / len(recent_scores)
        weight_key = f"weight:{agent}"
        
        # Sovereign Weight Logic: Higher score -> More tasks
        current_weight = float(sovereign_cache.get(weight_key) or 1.0)
        
        if avg_score > 0.85:
            new_weight = min(current_weight + 0.1, 2.0)
        elif avg_score < 0.65:
            new_weight = max(current_weight - 0.2, 0.1)
        else:
            new_weight = current_weight
            
        if HAS_REDIS:
            sovereign_cache.set(weight_key, str(new_weight))
        logger.info(f"[Evolution] Weight transition for {agent}: {current_weight} -> {new_weight}")

# Global Accessor
async def record_pulse(**kwargs):
    await AutonomousLearner.log_evolution_pulse(**kwargs)
