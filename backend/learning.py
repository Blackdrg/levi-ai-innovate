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

class AutonomousLearner:
    """
    Sovereign Evolution Engine.
    Observes neural pulses and adjusts model routing parameters.
    Hardened for autonomous feedback loops.
    """
    
    @staticmethod
    async def log_evolution_pulse(agent: str, query: str, score: float, metadata: Dict[str, Any]):
        """Logs a single neural pulse for historical analysis."""
        pulse_data = {
            "agent": agent,
            "query": query,
            "quality_score": score,
            "metadata": metadata,
            "timestamp": time.time()
        }
        
        # Persistence in the Global Ledger
        await sovereign_db.save_document("neural_pulses", f"{agent}_{int(time.time())}", pulse_data)
        
        # Real-time caching for the Evolution Dashboard
        pulse_list = eval(sovereign_cache.get("recent_pulses") or "[]")
        pulse_list.append(pulse_data)
        sovereign_cache.set("recent_pulses", str(pulse_list[-50:]))
        
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
            
        sovereign_cache.set(weight_key, str(new_weight))
        logger.info(f"[Evolution] Weight transition for {agent}: {current_weight} -> {new_weight}")

# Global Accessor
async def record_pulse(**kwargs):
    await AutonomousLearner.log_evolution_pulse(**kwargs)
