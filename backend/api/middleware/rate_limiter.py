import time
import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from backend.db.redis import r_async as redis_client, HAS_REDIS_ASYNC

logger = logging.getLogger(__name__)

class SlidingWindowRateLimiter:
    """
    Sovereign v13.1.0-Hardened-PROD Sliding Window Rate Limiter.
    Uses Redis ZSETs to enforce strict per-user cognitive pulse thresholds.
    """
    def __init__(self, r: redis_client, limit: int = 60, window: int = 60):
        self.r = r
        self.limit = limit
        self.window = window

    async def is_allowed(self, user_id: str) -> bool:
        if not HAS_REDIS_ASYNC:
            return True # Pulse permitted if Redis is offline (Failsafe)

        key = f"ratelimit:{user_id}"
        now = time.time()
        window_start = now - self.window

        try:
            pipe = self.r.pipeline()
            # 1. Purge entries older than the current window
            pipe.zremrangebyscore(key, 0, window_start)
            # 2. Add current pulse timestamp
            pipe.zadd(key, {str(now): now})
            # 3. Count active pulses in window
            pipe.zcard(key)
            # 4. Refresh TTL
            pipe.expire(key, self.window * 2)
            
            results = await pipe.execute()
            count = results[2]
            
            return count <= self.limit
        except Exception as e:
            logger.error(f"[RateLimit] Precise window failure: {e}")
            return True # Resilience: Allow on logic drift

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = 60, window: int = 60):
        super().__init__(app)
        self.limiter = SlidingWindowRateLimiter(redis_client, limit, window)

    async def dispatch(self, request: Request, call_next):
        # Identify User (v13.0 Absolute Monolith)
        # We check common auth headers as this middleware runs BEFORE standard auth dependency
        user_id = request.headers.get("X-User-ID", "global_anonymous")
        
        if not await self.limiter.is_allowed(user_id):
            logger.warning(f"[RateLimit] Blocked request from {user_id}")
            raise HTTPException(status_code=429, detail="Sovereign pulse threshold exceeded.")
            
        return await call_next(request)
