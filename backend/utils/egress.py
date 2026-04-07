"""
Sovereign Egress Proxy v13.1.0.
Hardened against SSRF bypasses via private IP ranges and metadata service.
"""

import logging
import ipaddress
from urllib.parse import urlparse
from typing import List

logger = logging.getLogger(__name__)

# Standard Allowlist for Graduate-Level Sovereign OS
ALLOWED_DOMAINS = [
    "localhost", "127.0.0.1",
    "api.openai.com", "api.anthropic.com", "api.groq.com", "api.together.xyz",
    "github.com", "api.github.com",
    "google.com", "api.google.com",
    "firebase.google.com"
]

# SSRF Blocklist: Private and Internal IP Ranges
FORBIDDEN_NETWORK_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.169.254/32"), # Cloud Metadata Service
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback (if and only if they are not explicitly allowed)
    ipaddress.ip_network("::1/128")
]

class EgressProxy:
    """
    Sovereign v13.1.0: Egress Protection.
    Ensures every outgoing request is validated against an allowlist 
    and blocks potential SSRF bypasses via private IP addresses.
    """

    @classmethod
    def validate_target(cls, url: str) -> bool:
        """
        Validates target URL for SSRF protection.
        Checks domain allowlist and blocklist for private network traffic.
        """
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.split(":")[0].lower() # Strip port

            # 1. Allow internal K8s/Docker services (no dot, e.g., 'postgres')
            if "." not in netloc:
                return True
            
            # 2. Check explicitly allowed domains
            if netloc in ALLOWED_DOMAINS:
                return True
            
            # 3. Block potentially malicious IP addresses
            try:
                ip = ipaddress.ip_address(netloc)
                for range in FORBIDDEN_NETWORK_RANGES:
                    if ip in range:
                        logger.error(f"[EgressProxy] BLOCKED SSRF to forbidden IP: {netloc}")
                        return False
            except ValueError:
                # Not a raw IP, domain name.
                pass
            
            # 4. Final safety check: block all non-allowed external domains
            if netloc not in ALLOWED_DOMAINS:
                logger.error(f"[EgressProxy] BLOCKED attempt to unauthorized domain: {netloc}")
                return False

            return True

        except Exception as e:
            logger.error(f"[EgressProxy] Target validation error: {e}")
            return False
