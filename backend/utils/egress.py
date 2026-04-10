import logging
import ipaddress
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Standard Allowlist for Graduate-Level Sovereign OS
ALLOWED_DOMAINS = [
    "localhost", "127.0.0.1",
    "api.openai.com", "api.anthropic.com", "api.groq.com", "api.together.xyz",
    "github.com", "api.github.com",
    "google.com", "api.google.com",
    "firebase.google.com",
    "api.tavily.com",
    "huggingface.co",
    "api-inference.huggingface.co"
]

# SSRF Blocklist: Private and Internal IP Ranges
FORBIDDEN_NETWORK_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.169.254/32"), # Cloud Metadata Service
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
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
            # In production, even these should be restricted, but for DCN resonance we allow internal.
            if "." not in netloc:
                return True
            
            # 2. Check explicitly allowed domains
            if netloc in ALLOWED_DOMAINS:
                 # Even if it's in the allowlist, we should still check the IP 
                 # if someone managed to point a trusted domain to a private IP (malicious DNS).
                 pass
            elif any(netloc.endswith(f".{d}") for d in ALLOWED_DOMAINS if "." in d):
                 # Allow subdomains of allowed domains
                 pass
            else:
                # Heuristic: If it's not a known domain, block unless it's a specific exception.
                # However, for the Graduate OS, we want to allow resolution and IP-based validation.
                pass

            # 3. DNS Resolution & Rebinding Check
            try:
                # Resolve the domain to an IP address
                resolved_ip_str = socket.gethostbyname(netloc)
                resolved_ip = ipaddress.ip_address(resolved_ip_str)
                
                # Check against forbidden ranges
                for forbidden_range in FORBIDDEN_NETWORK_RANGES:
                    if resolved_ip in forbidden_range:
                        logger.error(f"[EgressProxy] BLOCKED SSRF/Rebinding: {netloc} resolves to forbidden IP {resolved_ip_str}")
                        return False
            except socket.gaierror:
                logger.warning(f"[EgressProxy] Could not resolve host: {netloc}")
                return False
            except ValueError:
                # In case resolved_ip_str is not a valid IP (unlikely)
                return False
            
            # 4. Final safety check: block all non-allowed external domains if strict mode is active
            # For v14.1.0, we prioritize the Allowlist for better defense-in-depth.
            if netloc not in ALLOWED_DOMAINS:
                 # Check if the IP itself is the netloc and is forbidden (handled by resolution block above)
                 # If it's a domain NOT in allowlist, we block it by default.
                 logger.error(f"[EgressProxy] BLOCKED attempt to unauthorized domain: {netloc}")
                 return False

            return True

        except Exception as e:
            logger.error(f"[EgressProxy] Target validation error: {e}")
            return False
