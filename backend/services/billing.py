import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from backend.redis_client import cache
from backend.db.postgres import get_db
from backend.db.models import MissionMetric

logger = logging.getLogger(__name__)

class CognitiveBilling:
    """
    Sovereign Cognitive Billing v13.0.0.
    Calculates and tracks Cognitive Unit (CU) consumption across the BrainPulse.
    """
    
    # CU Multipliers
    MODEL_WEIGHTS = {
        "llama-3.1-8b": 1.0,
        "llama-3.1-70b": 5.0,
        "local": 0.5 # Local inference is cheaper
    }
    
    BASE_AGENT_COST = 0.5 # CU per agent call
    COMPUTE_WEIGHT = 0.01 # CU per 100ms of execution

    @classmethod
    def calculate_cu(cls, tokens: int, model: str, agent_calls: int, latency_ms: float) -> float:
        """
        Formal CU Formula:
        CU = (Tokens * ModelWeight) + (Agents * BaseCost) + (Latency * ComputeWeight)
        """
        model_weight = cls.MODEL_WEIGHTS.get(model, 1.0)
        
        cu_tokens = (tokens / 1000.0) * model_weight
        cu_agents = agent_calls * cls.BASE_AGENT_COST
        cu_compute = (latency_ms / 100.0) * cls.COMPUTE_WEIGHT
        
        total_cu = cu_tokens + cu_agents + cu_compute
        return round(total_cu, 4)

    @classmethod
    async def record_transaction(
        self, 
        user_id: str, 
        mission_id: str, 
        cu_amount: float,
        tenant_id: str = "global"
    ):
        """
        Records the CU consumption to the Postgres ledger and updates Redis quota.
        """
        logger.info(f"[Billing] User {user_id} consumed {cu_amount} CU for mission {mission_id}")
        
        # 1. Update SQL Ledger
        # (Simplified: in a real app would use a specific Transactions table)
        # We'll update the mission_metrics table for now.
        
        # 2. Update Redis Quota (Soft Limit)
        quota_key = f"cu_quota:{user_id}"
        current_usage = cache.get(quota_key) or 0.0
        new_usage = float(current_usage) + cu_amount
        cache.set(quota_key, new_usage, ex=2592000) # 30 day TTL

    @classmethod
    def check_quota(cls, user_id: str, threshold: float = 1000.0) -> bool:
        """Checks if the user has exceeded their cognitive budget."""
        usage = float(cache.get(f"cu_quota:{user_id}") or 0.0)
        if usage > threshold:
            logger.warning(f"[Billing] User {user_id} exceeded CU threshold: {usage}/{threshold}")
            return False
        return True
