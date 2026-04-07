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
        
        # 🛡️ Graduation Standards: Audit-Ready Header Injection
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; object-src 'none'; img-src 'self' data:; connect-src 'self' ws: wss:"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Sovereign-Version"] = "v1.0.0-RC1"
        
        return response
