"""
Sovereign Shield Middleware v8.
Standardized auth and security middleware for the backend logic.
"""

import logging
import time
from typing import Callable, Coroutine, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class SovereignShieldMiddleware(BaseHTTPMiddleware):
    """
    LEVI-AI v8: Sovereign Shield Middleware.
    Handles global request logging, latency tracking, and basic security headers.
    """
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Coroutine[Any, Any, Response]]) -> Response:
        start_time = time.perf_counter()
        
        # 1. Pre-processing (Headers/WAF logic could go here)
        
        # 2. Sequential Call
        response = await call_next(request)
        
        # 3. Post-processing (Audit Point 25: Security Headers)
        process_time = (time.perf_counter() - start_time) * 1000
        response.headers["X-Process-Time-Ms"] = str(int(process_time))
        response.headers["X-Sovereign-Shield"] = "v13.1.0-active"
        
        # Hardened Perimeter Headers
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none';"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 4. Global Logging
        if request.url.path not in ("/health", "/metrics", "/favicon.ico"):
            logger.info(
                "[%s] %s %s - %d (%.2fms)",
                request.client.host if request.client else "unknown",
                request.method,
                request.url.path,
                response.status_code,
                process_time
            )
            
        return response
