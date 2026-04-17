import time
import logging
import json
import os
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from backend.db.redis import r_async as redis_client, HAS_REDIS_ASYNC
from backend.db.postgres import PostgresDB
from backend.db.models import User
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Tiered Limit Definitions (v14.0 Sovereign Policy)
TIER_LIMITS = {
    "free":      {"rpm": 5,   "rpd": 50,   "concurrency": 1},
    "pro":       {"rpm": 30,  "rpd": 1000, "concurrency": 5},
    "sovereign": {"rpm": 120, "rpd": 5000, "concurrency": 20}
}

# 🛡️ Sovereign v16.3: Abuse Detection Thresholds
ABUSE_THRESHOLDS = {
    "burst_threshold_rpm": 10, # Rapid bursts for Free tier
    "rapid_fire_ms": 500,       # Minimum ms between requests
}

class SlidingWindowRateLimiter:
    """
    Sovereign v14.0 Sliding Window Rate Limiter.
    Enforces tiered RPM (Minute) and RPD (Day) thresholds.
    """
    def __init__(self, r: redis_client):
        self.r = r

    async def is_allowed(self, user_id: str) -> bool:
        if not HAS_REDIS_ASYNC:
            return True

        # 🛡️ Phase 3: Database-Verified Tiering
        tier = await self._get_verified_tier(user_id)
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
            
            # 🌐 Phase 4: Global Quota Sync (If near limit, gossip to other regions)
            if results[6] > (tier_config["rpd"] * 0.8):
                from backend.utils.global_gossip import global_swarm_bridge
                if global_swarm_bridge.publisher:
                    try:
                        # Ensure bridge is initialized at least once
                        if not global_swarm_bridge.topic_path:
                            await global_swarm_bridge.initialize()
                        
                        global_swarm_bridge.publisher.publish(
                            global_swarm_bridge.topic_path,
                            json.dumps({
                                "type": "QUOTA_ALERT",
                                "user_id": user_id,
                                "consumed": results[6],
                                "source_region": os.getenv("GCP_REGION", "global"),
                                "is_global": True
                            }).encode("utf-8")
                        )
                    except Exception as gossip_err:
                        logger.warning(f"[RateLimit] Global sync failed: {gossip_err}")


            if results[2] > tier_config["rpm"] or results[6] > tier_config["rpd"]:
                return False
                
            return True
        except Exception as e:
            logger.error(f"[RateLimit] Tiered failure: {e}")
            return True

    async def _get_verified_tier(self, user_id: str) -> str:
        """Fetch verified tier from regional Postgres database."""
        if user_id == "global_anonymous": return "free"
        
        try:
            async with PostgresDB._session_factory() as session:
                stmt = select(User).where(User.id == user_id)
                res = await session.execute(stmt)
                user = res.scalar_one_or_none()
                return user.tier if user else "free"
        except:
            return "free"

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.limiter = SlidingWindowRateLimiter(redis_client)

    async def dispatch(self, request: Request, call_next):
        user_id = request.headers.get("X-User-ID", "global_anonymous")
        
        if not await self.limiter.is_allowed(user_id):
            logger.warning(f"[RateLimit] Blocked request from {user_id}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Sovereign pulse threshold exceeded. Please scale your cognitive tier."}
            )
            
        return await call_next(request)
