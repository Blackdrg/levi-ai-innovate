"""
LEVI-AI Sovereign OS v14.0.0-Autonomous-SOVEREIGN [ACTIVE V14 COMPONENT].
Egress Proxy: Strict SSRF allowlist and cognitive isolation.
"""

import logging
import httpx
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

ALLOWED_EGRESS_DOMAINS = {
    "api.tavily.com",       # Search API
    "serpapi.com",          # Alt search
    # Everything else is BLOCKED by default
}

class SSRFBlockedError(Exception):
    """Raised when an egress request is blocked by the Sovereign SSRF wall."""
    pass

class EgressProxy:
    """
    Sovereign Egress Proxy v13.0.0.
    Enforces 'Deny-by-Default' and domain-level integrity.
    """
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)

    async def get(self, url: str, **kwargs):
        domain = urlparse(url).netloc.lower()
        
        # v13.0 Integrity Check: SSRF Hardening
        if not any(domain.endswith(d) for d in ALLOWED_EGRESS_DOMAINS):
            logger.warning(f"[Egress-v13] SSRF Blocked Attempt: {domain}")
            raise SSRFBlockedError(
                f"Egress blocked: {domain} not in Sovereign Allowlist"
            )
            
        logger.info(f"[Egress-v13] Link allowed: {domain}")
        return await self._client.get(url, **kwargs)

    async def post(self, url: str, **kwargs):
        domain = urlparse(url).netloc.lower()
        if not any(domain.endswith(d) for d in ALLOWED_EGRESS_DOMAINS):
            logger.warning(f"[Egress-v13] SSRF Blocked POST: {domain}")
            raise SSRFBlockedError(f"Egress blocked (POST): {domain}")
        return await self._client.post(url, **kwargs)

    async def close(self):
        await self._client.aclose()

# Global Sovereign Egress Instance
egress_proxy = EgressProxy()
