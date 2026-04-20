import time
import logging
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from backend.db.redis import get_redis_client, HAS_REDIS
from backend.config.system import TIERS

logger = logging.getLogger(__name__)

class SovereignRateLimiter(BaseHTTPMiddleware):
    """
    Sovereign v13.0: Tier-Aware Distributed Rate Limiter.
    Uses Redis sliding window counters to enforce fair usage and cost safety.
    """
    
    async def dispatch(self, request: Request, call_next):
        if not HAS_REDIS:
            return await call_next(request)
            
        # 1. Identity Detection (Skip for health checks)
        if request.url.path in ["/health", "/metrics", "/docs"]:
            return await call_next(request)
            
        # 2. Extract User/Tier (Placeholder until Auth matches)
        # In production, this runs AFTER Auth middleware or extracts from JWT
        user_id = request.headers.get("X-User-ID", "anonymous")
        tier = request.headers.get("X-Tier", "free")
        
        # 3. Limit Logic
        limit_config = TIERS.get(tier, TIERS["free"])
        max_requests = limit_config.get("daily_limit", 100)
        
        # Sliding Window logic (1-hour windows for granularity)
        window_sec = 3600
        current_time = int(time.time())
        window_key = f"rate_limit:{user_id}:{current_time // window_sec}"
        
        try:
            redis_client = get_redis_client()
            if not redis_client:
                return await call_next(request)
            count = redis_client.incr(window_key)
            if count == 1:
                redis_client.expire(window_key, window_sec * 2)
                
            if count > (max_requests // 24): # Simple hourly distribution
                logger.warning(f"Rate Limit Exceeded: User {user_id} tier {tier} ({count}/{max_requests//24})")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded for tier '{tier}'. Try again in 1 hour."
                )
        except Exception as e:
            if isinstance(e, HTTPException): raise e
            logger.error(f"Rate limiter failure: {e}")
            
        return await call_next(request)
