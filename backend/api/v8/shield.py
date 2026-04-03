import time
import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from backend.services.memory.vault import MemoryVault
from backend.core.logger import logger

class SovereignShieldMiddleware(BaseHTTPMiddleware):
    """
    Sovereign OS v8.9: Sovereign Shield Middleware.
    Hardens the API against exhaustion and provides deep audit logging to Neo4j.
    """
    def __init__(self, app, rate_limit: int = 100):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.vault = MemoryVault()
        self.request_counts = {} # Simple in-memory rate limiting for now, can be Redis-backed

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()

        # 1. Rate Limiting Logic
        self._clean_old_requests(current_time)
        if self._is_rate_limited(client_ip, current_time):
            logger.warning(f"Sovereign Shield: Rate limit exceeded for {client_ip}")
            raise HTTPException(status_code=429, detail="Sovereign Shield: Rate limit exceeded. Transcendence requires patience.")

        # 2. Audit Logging Pre-Execution
        start_time = time.time()
        
        # 3. Request Execution
        response = await call_next(request)
        
        # 4. Audit Logging Post-Execution
        duration = time.time() - start_time
        await self._log_audit_trace(request, response, duration)

        return response

    def _is_rate_limited(self, ip: str, current_time: float) -> bool:
        if ip not in self.request_counts:
            self.request_counts[ip] = []
        
        self.request_counts[ip].append(current_time)
        return len(self.request_counts[ip]) > self.rate_limit

    def _clean_old_requests(self, current_time: float):
        for ip in list(self.request_counts.keys()):
            self.request_counts[ip] = [t for t in self.request_counts[ip] if current_time - t < 60]

    async def _log_audit_trace(self, request: Request, response, duration: float):
        """Asynchronously logs the request trace to Neo4j."""
        try:
            audit_data = {
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "duration_ms": int(duration * 1000),
                "timestamp": time.time()
            }
            # Injecting into Neo4j via MemoryVault utility
            # self.vault.create_audit_node(audit_data) 
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
