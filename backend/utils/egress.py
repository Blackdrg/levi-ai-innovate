import logging
import ipaddress
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Standard Allowlist for Sovereign OS v15.0
ALLOWED_DOMAINS = [
    "localhost", "127.0.0.1",
    "google.com", "api.google.com",
    "github.com", "api.github.com",
    "huggingface.co", "api-inference.huggingface.co",
    "openai.com", "api.openai.com",
    "anthropic.com", "api.anthropic.com",
    "groq.com", "api.groq.com",
    "together.xyz", "api.together.xyz",
    "tavily.com", "api.tavily.com",
    "firebase.google.com"
]

# SSRF Blocklist: Private and Internal IP Ranges
FORBIDDEN_NETWORK_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.169.254/32"), # Cloud Metadata
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("0.0.0.0/8")
]

class EgressProxy:
    """
    Sovereign v14.1.0: Hardened Egress Protection.
    Implements DNS-Rebinding prevention via pre-request resolution.
    """

    @classmethod
    def validate_target(cls, url: str) -> bool:
        """
        Validates target URL for SSRF and DNS-Rebinding protection.
        """
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
                
            netloc = parsed.netloc.split(":")[0].lower() # Strip port

            # 1. Allow internal K8s/Docker services (no dot, e.g., 'postgres')
            # For v14.1.0 Graduation, we block these by default unless explicitly allowed.
            if "." not in netloc:
                if netloc not in ALLOWED_DOMAINS:
                    logger.warning(f"[EgressProxy] BLOCKED internal service access: {netloc}")
                    return False
                return True
            
            # 2. Check explicitly allowed domains & subdomains
            is_allowed_domain = False
            if netloc in ALLOWED_DOMAINS:
                 is_allowed_domain = True
            elif any(netloc.endswith(f".{d}") for d in ALLOWED_DOMAINS if "." in d):
                 is_allowed_domain = True
            
            if not is_allowed_domain:
                logger.error(f"[EgressProxy] BLOCKED attempt to unauthorized domain: {netloc}")
                return False

            # 3. DNS Resolution & Rebinding Check (Defense-in-Depth)
            try:
                # Resolve the domain to an IP address
                resolved_ip_str = socket.gethostbyname(netloc)
                resolved_ip = ipaddress.ip_address(resolved_ip_str)
                
                # Check against forbidden ranges
                for forbidden_range in FORBIDDEN_NETWORK_RANGES:
                    if resolved_ip in forbidden_range:
                        logger.critical(f"[EgressProxy] SSRF/REBINDING ALERT: {netloc} resolves to forbidden IP {resolved_ip_str}")
                        return False
            except socket.gaierror:
                logger.warning(f"[EgressProxy] Could not resolve host: {netloc}")
                return False
            except ValueError:
                return False

            return True

        except Exception as e:
            logger.error(f"[EgressProxy] Target validation error: {e}")
            return False
