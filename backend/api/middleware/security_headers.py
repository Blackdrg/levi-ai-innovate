from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import os

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Sovereign Security Headers v13.0.0.
    Injects 'Audit-Ready' headers into every outbound API pulse.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 🛡️ Graduation Standards: Audit-Ready Header Injection (v13.1.0)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "object-src 'none'; "
            "img-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "style-src 'self' 'unsafe-inline'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["X-Sovereign-Version"] = "v13.1.0-Hardened-PROD"
        
        return response
