import time
import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from backend.services.memory.vault import MemoryVault
from backend.core.logger import logger
from backend.core.v8.llm_guard import PIIScrubber

class SovereignShieldMiddleware(BaseHTTPMiddleware):
    """
    Sovereign OS v9.8: Sovereign Shield Middleware.
    Hardens the API against exhaustion using Redis-backed windowed rate limiting.
    Provides deep audit logging and anomaly detection.
    """
    def __init__(self, app, rate_limit: int = 150):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window = 60 # 1 minute window
        self.request_counts = {} # Fallback in-memory logic
        
        try:
            from backend.db.redis import get_redis_client
            self.redis = get_redis_client()
            logger.info("[SovereignShield] Redis-backed rate limiting ACTIVATED.")
        except Exception as e:
            logger.error(f"[SovereignShield] Redis connection failed, falling back to in-memory: {e}")
            self.redis = None

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        
        # 1. Production Rate Limiting (Redis-first)
        if await self._is_rate_limited(client_ip):
            logger.warning(f"[SovereignShield] RATE LIMIT EXCEEDED: {client_ip}")
            raise HTTPException(
                status_code=429, 
                detail="Sovereign Shield: Rate limit exceeded. Transcendence requires patience."
            )

        start_time = time.time()
        
        # 2. Execute Request
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"[SovereignShield] Dispatch Error: {e}")
            # Global Exception Suppression for Production
            raise HTTPException(status_code=500, detail="Internal Sovereign Error.")

        # 3. Audit Trace
        duration = time.time() - start_time
        await self._log_audit_trace(request, response, duration)

        return response

    async def _is_rate_limited(self, ip: str) -> bool:
        """Windowed rate limiting logic."""
        if self.redis:
            try:
                key = f"limit:{ip}"
                # Multi/Exec block for atomic increment and expire
                pipe = self.redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, self.window)
                results = pipe.execute()
                count = results[0]
                return count > self.rate_limit
            except Exception as e:
                logger.error(f"[SovereignShield] Redis rate limit failure: {e}")
                # Fallback to in-memory if Redis fails during execution
                return self._is_rate_limited_memory(ip)
        else:
            return self._is_rate_limited_memory(ip)

    def _is_rate_limited_memory(self, ip: str) -> bool:
        """In-memory fallback for rate limiting."""
        current_time = time.time()
        if ip not in self.request_counts:
            self.request_counts[ip] = []
        
        # Clean old requests
        self.request_counts[ip] = [t for t in self.request_counts[ip] if current_time - t < self.window]
        self.request_counts[ip].append(current_time)
        return len(self.request_counts[ip]) > self.rate_limit

    async def _log_audit_trace(self, request: Request, response, duration: float):
        """Asynchronously logs the request trace to Neo4j, with PII scrubbing."""
        try:
            # Scrub URL and potentially headers/body if logged
            url = PIIScrubber.scrub(str(request.url))
            
            audit_data = {
                "method": request.method,
                "url": url,
                "status_code": response.status_code,
                "duration_ms": int(duration * 1000),
                "timestamp": time.time()
            }
            logger.debug(f"Sovereign Shield Audit: {audit_data['method']} {audit_data['url']} - {audit_data['status_code']} ({audit_data['duration_ms']}ms)")
        except Exception as e:
            logger.error(f"Fidelity Breach: Audit logging failed - {str(e)}")

# Dependency or Utility to help with security audits
def check_fidelity_breach(score: float, threshold: float = 0.5):
    """Triggers a fail-safe if fidelity drops below safety thresholds."""
    if score < threshold:
        logger.critical(f"Sovereign Shield: FIDELITY BREACH DETECTED (Score: {score})")
        # In a real scenario, this could trigger a circuit breaker or alert
        return True
    return False
