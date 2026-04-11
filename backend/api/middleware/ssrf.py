"""
LEVI-AI Sovereign OS v14.1.0 (Audit RC1).
SSRF & DNS Rebinding Ingress Middleware.
Protects internal endpoints from unauthorized cross-service access via spoofed headers.
"""

import logging
import ipaddress
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Forbidden internal ranges that should never be reachable via public ingress
FORBIDDEN_INGRESS_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.169.254/32"),
    ipaddress.ip_network("::1/128"),
]

class SSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_host = request.client.host if request.client else "unknown"
        
        # 🛡️ Protection 1: Prevent Ingress from Private/Loopback (if sitting behind public LB)
        # In a real production setup, we'd check X-Forwarded-For as well.
        try:
            client_ip = ipaddress.ip_address(client_host)
            for forbidden in FORBIDDEN_INGRESS_NETWORKS:
                if client_ip in forbidden:
                    logger.critical(f"[Security] SSRF Ingress Attempt! Blocked request from {client_host}")
                    return Response(content="Security Violation: Internal access denied.", status_code=403)
        except ValueError:
            pass # Not a valid IP, probably a hostname we can't easily block here

        # 🛡️ Protection 2: Host Header Validation
        # Prevents DNS rebinding against the server itself if it's not configured with a strict Host header
        host_header = request.headers.get("host", "").split(":")[0]
        if host_header in ["localhost", "127.0.0.1", "0.0.0.0"]:
            # Only allow localhost for local dev; in production this must be blocked
            if os.getenv("ENVIRONMENT") == "production":
                 logger.critical(f"[Security] Host Header Violation (DNS Rebinding Attempt): {host_header}")
                 return Response(content="Security Violation: Invalid Host Header.", status_code=400)

        return await call_next(request)
