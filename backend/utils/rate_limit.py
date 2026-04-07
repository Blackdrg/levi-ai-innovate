"""
Sovereign Rate Limiter v9.8.1.
Implements Redis-backed sliding window rate limiting for autonomous agents and API endpoints.
"""

import time
import logging
from typing import Tuple
from backend.db.redis import r as redis_client, HAS_REDIS

logger = logging.getLogger(__name__)

class SovereignRateLimiter:
    """
    Sovereign Resilience Controller.
    Prevents Agent Storms and infrastructure exhaustion.
    """
    
    @classmethod
    def is_allowed(cls, key: str, limit: int, window_seconds: int = 3600) -> Tuple[bool, int]:
        """
        Sliding Window Rate Limiter.
        Returns (is_allowed, current_count).
        """
        if not HAS_REDIS or not redis_client:
            return True, 0 # Fail-open if Redis is down (Production should have fail-over)

        now = time.time()
        pipe = redis_client.pipeline()
        
        # Remove old requests
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Count current requests
        pipe.zcard(key)
        # Set expiry for the key
        pipe.expire(key, window_seconds)
        
        results = pipe.execute()
        current_count = results[2]
        
        allowed = current_count <= limit
        if not allowed:
            logger.warning(f"[RateLimiter] Limit exceeded for {key}: {current_count}/{limit}")
            
        return allowed, current_count

# Helper for executor
async def check_agent_limit(user_id: str, agent_name: str, limit: int = 50) -> bool:
    """Checks if a user is within their quota for a specific agent."""
    key = f"rate_limit:{user_id}:{agent_name}"
    allowed, count = SovereignRateLimiter.is_allowed(key, limit)
    return allowed
