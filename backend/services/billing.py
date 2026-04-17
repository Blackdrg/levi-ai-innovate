import logging
from backend.redis_client import cache

logger = logging.getLogger(__name__)

class PricingTier:
    FREE = {"cu_limit": 1000.0, "max_dag_depth": 3, "priority": 1}
    PRO = {"cu_limit": 10000.0, "max_dag_depth": 8, "priority": 5}
    ENTERPRISE = {"cu_limit": 1000000.0, "max_dag_depth": 15, "priority": 10}

class CognitiveBilling:
    """
    Sovereign Cognitive Billing v14.1 [PROTOTYPE - STUB].
    Calculates consumption and manages Pricing Tiers.
    NOTE: Currently operates with hardcoded 'FREE' tier logic as a prototype.
    """
    
    # CU Multipliers
    MODEL_WEIGHTS = {
        "llama-3.1-8b": 1.0,
        "llama-3.1-70b": 5.0,
        "local": 0.5,
        "gpt-4o": 10.0 # External premium
    }
    
    BASE_AGENT_COST = 0.5
    COMPUTE_WEIGHT = 0.01

    @classmethod
    def get_user_tier(cls, user_id: str) -> dict:
        """Determines the pricing tier for a user."""
        # Standard: Free. Pro/Enterprise would be stored in Firestore/Postgres.
        # This is a stub that would fetch from the user profile.
        return PricingTier.FREE

    @classmethod
    def calculate_cu(cls, tokens: int, model: str, agent_calls: int, latency_ms: float) -> float:
        model_weight = cls.MODEL_WEIGHTS.get(model, 1.0)
        cu_tokens = (tokens / 1000.0) * model_weight
        cu_agents = agent_calls * cls.BASE_AGENT_COST
        cu_compute = (latency_ms / 100.0) * cls.COMPUTE_WEIGHT
        return round(cu_tokens + cu_agents + cu_compute, 4)

    @classmethod
    async def record_transaction(cls, user_id: str, mission_id: str, cu_amount: float):
        logger.info(f"[Billing] User {user_id} consumed {cu_amount} CU")
        quota_key = f"cu_quota:{user_id}"
        
        from backend.db.redis import r as redis_client
        if redis_client:
            redis_client.incrbyfloat(quota_key, cu_amount)
            redis_client.expire(quota_key, 2592000)

    @classmethod
    def check_quota(cls, user_id: str) -> bool:
        """Checks if user has exceeded their tier budget."""
        tier = cls.get_user_tier(user_id)
        from backend.db.redis import r as redis_client
        usage = float(redis_client.get(f"cu_quota:{user_id}") or 0.0) if redis_client else 0.0
        
        if usage > tier["cu_limit"]:
            logger.warning(f"[Billing] Quota EXCEEDED for {user_id}: {usage}/{tier['cu_limit']}")
            return False
        return True
