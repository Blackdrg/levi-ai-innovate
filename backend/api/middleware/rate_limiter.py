import time
import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from backend.db.redis import r_async as redis_client, HAS_REDIS_ASYNC

logger = logging.getLogger(__name__)

# Tiered Limit Definitions (v14.0 Sovereign Policy)
TIER_LIMITS = {
    "free":      {"rpm": 5,   "rpd": 50,   "concurrency": 1},
    "pro":       {"rpm": 30,  "rpd": 1000, "concurrency": 5},
    "sovereign": {"rpm": 120, "rpd": 5000, "concurrency": 20}
}

class SlidingWindowRateLimiter:
    """
    Sovereign v14.0 Sliding Window Rate Limiter.
    Enforces tiered RPM (Minute) and RPD (Day) thresholds.
    """
    def __init__(self, r: redis_client):
        self.r = r

    async def is_allowed(self, user_id: str, tier: str = "free") -> bool:
        if not HAS_REDIS_ASYNC:
            return True

        tier_config = TIER_LIMITS.get(tier.lower(), TIER_LIMITS["free"])
        now = time.time()
        rpm_key = f"rl:rpm:{user_id}"
        rpd_key = f"rl:rpd:{user_id}"

        try:
            pipe = self.r.pipeline()
            pipe.zremrangebyscore(rpm_key, 0, now - 60)
            pipe.zadd(rpm_key, {str(now): now})
            pipe.zcard(rpm_key)
            pipe.expire(rpm_key, 120)
            
            pipe.zremrangebyscore(rpd_key, 0, now - 86400)
            pipe.zadd(rpd_key, {str(now): now})
            pipe.zcard(rpd_key)
            pipe.expire(rpd_key, 172800)
            
            results = await pipe.execute()
            if results[2] > tier_config["rpm"] or results[6] > tier_config["rpd"]:
                return False
                
            return True
        except Exception as e:
            logger.error(f"[RateLimit] Tiered failure: {e}")
            return True

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.limiter = SlidingWindowRateLimiter(redis_client)

    async def dispatch(self, request: Request, call_next):
        user_id = request.headers.get("X-User-ID", "global_anonymous")
        user_tier = request.headers.get("X-User-Tier", "free")
        
        if not await self.limiter.is_allowed(user_id, user_tier):
            logger.warning(f"[RateLimit] Blocked request from {user_id} (Tier: {user_tier})")
            raise HTTPException(status_code=429, detail=f"Sovereign {user_tier} pulse threshold exceeded.")
            
        return await call_next(request)
