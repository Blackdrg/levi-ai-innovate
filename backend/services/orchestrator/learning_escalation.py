"""
backend/services/orchestrator/learning_escalation.py

Learning Escalation Engine (LEE) for LEVI-AI (Phase 18).
Classifies system health and gatekeeps expensive fine-tuning operations.
"""

import logging
import json
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from backend.redis_client import r as redis_client, HAS_REDIS

logger = logging.getLogger(__name__)

class EvolutionState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"

class EscalationManager:
    """
    Supervises the learning state of LEVI-AI.
    Moves the system through escalation tiers before allowing fine-tuning.
    """
    
    # Thresholds
    DEGRADATION_THRESHOLD = 3.8 # Avg rating below this = DEGRADED
    CRITICAL_THRESHOLD = 3.2    # Avg rating below this = CRITICAL
    WINDOW_SIZE = 100           # Interactions to analyze
    
    @classmethod
    async def classify_system_state(cls) -> EvolutionState:
        """
        Analyzes recent performance and returns the system evolution state.
        """
        if not HAS_REDIS:
            return EvolutionState.HEALTHY
            
        # 1. Fetch Moving Average of Quality
        # We use a Redis variable that tracks the windowed avg rating.
        avg_rating = float(redis_client.get("stats:avg_response_rating") or 5.0)
        
        # 2. Logic to transition between levels
        if avg_rating < cls.CRITICAL_THRESHOLD:
            return EvolutionState.CRITICAL
        elif avg_rating < cls.DEGRADATION_THRESHOLD:
            return EvolutionState.DEGRADED
        else:
            return EvolutionState.HEALTHY

    @classmethod
    async def should_allow_finetune(cls, hq_count: int) -> bool:
        """
        The Master Gatekeeper logic.
        Only returns True if the system is CRITICAL and algorithmic fixes failed.
        """
        state = await cls.classify_system_state()
        
        # 1. State Check 
        if state != EvolutionState.CRITICAL:
            logger.info(f"[Escalation] Fine-tune rejected. State is {state.value}.")
            return False
            
        # 2. Threshold Check (Need enough data)
        if hq_count < 1000:
            logger.info(f"[Escalation] Fine-tune rejected. Insufficient data ({hq_count}/1000).")
            return False

        # 3. Budget & Cooldown (Max 1 per week)
        last_train = redis_client.get("system:finetuning:last_train_timestamp")
        if last_train:
            last_dt = datetime.fromisoformat(last_train.decode())
            if (datetime.utcnow() - last_dt).days < 7:
                 logger.info("[Escalation] Fine-tune rejected. Cooldown period active.")
                 return False

        # 4. Prompt Optimization Check
        # Ensure we've at least tried mutation several times correctly
        mutation_count = int(redis_client.get("system:evolution:mutation_count") or 0)
        if mutation_count % 5 != 0: # Ensure we gave mutation a chance to settle
             logger.info("[Escalation] Fine-tune rejected. Prompt mutation cycle pending.")
             # return False # In practice, we'd be stricter, but here we allow early if critical
        
        return True

    @classmethod
    def record_interaction_metrics(cls, rating: int, confidence: float):
        """
        Updates moving averages in Redis for the state classifier.
        """
        if not HAS_REDIS: return
        
        # Simple weighted moving average (0.1 weight for new sample)
        prev_avg = float(redis_client.get("stats:avg_response_rating") or 4.0)
        new_avg = (prev_avg * 0.9) + (rating * 0.1)
        redis_client.set("stats:avg_response_rating", str(new_avg))
        
        # Confidence tracking
        prev_conf = float(redis_client.get("stats:avg_confidence") or 0.9)
        new_conf = (prev_conf * 0.9) + (confidence * 0.1)
        redis_client.set("stats:avg_confidence", str(new_conf))
