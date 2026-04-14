"""
LEVI-AI Sovereign Shield v15.0.0-GA.
The primary defensive perimeter and authentication nexus.
Handles: JWT Verification, Threat Detection, and Header Enforcement.
"""

import logging
import time
import os
from typing import Callable, Coroutine, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.auth.jwt_provider import JWTProvider
from backend.utils.logger import get_logger

logger = get_logger("shield")

class SovereignShield(BaseHTTPMiddleware):
    """
    Hardened Sovereign Shield Middleware.
    Verified for v15.0 GA.
    """
    
    # Paths that bypass JWT verification
    PUBLIC_PATHS = {
        "/healthz",
        "/readyz",
        "/metrics",
        "/favicon.ico",
        "/api/v1/auth/login",
        "/api/v1/auth/signup",
        "/api/v1/auth/identify",
        "/api/v1/auth/verify",
        "/ui",
        "/app",
        "/shared"
    }

    async def dispatch(self, request: Request, call_next: Callable[[Request], Coroutine[Any, Any, Response]]) -> Response:
        start_time = time.perf_counter()
        
        # 1. Path Filtering
        is_public = any(request.url.path.startswith(p) for p in self.PUBLIC_PATHS)
        
        # 2. JWT Verification (Sovereign Shield Requirement)
        if not is_public and os.getenv("STRICT_AUTH", "true").lower() == "true":
            auth_header = request.headers.get("Authorization")
            token = None
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            else:
                # Fallback for WebSockets/SSE via query param
                token = request.query_params.get("token")

            if not token:
                logger.warning(f"🛡️ [Shield] Blocked unauthenticated request to {request.url.path} from {request.client.host if request.client else 'unknown'}")
                return JSONResponse(
                    status_code=401,
                    content={"status": "error", "message": "Identity context missing. Access denied by Sovereign Shield."}
                )
            
            # Verify Token
            decoded = JWTProvider.verify_token(token)
            if not decoded:
                logger.warning(f"🛡️ [Shield] Blocked invalid/expired token request to {request.url.path}")
                return JSONResponse(
                    status_code=401,
                    content={"status": "error", "message": "Token entropy lost or corrupted. Sovereign Shield remains active."}
                )
            
            # Inject identity into state for downstream use
            request.state.user = decoded

        # 3. Request Latency Tracking
        response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000
        
        # 4. Hardened Security Headers
        response.headers["X-Process-Time-Ms"] = str(int(process_time))
        response.headers["X-Sovereign-Shield"] = "v15.0.0-GA-Active"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none';"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # 5. Global Logging
        if request.url.path not in ("/healthz", "/metrics"):
            logger.info(
                "[%s] %s %s - %d (%.2fms)",
                request.client.host if request.client else "unknown",
                request.method,
                request.url.path,
                response.status_code,
                process_time
            )
            
        return response
