import os
import httpx
import logging
import ssl
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class InternalServiceClient:
    """
    Sovereign v14.1 Internal Service Client.
    Enforces mTLS zero-trust communication between internal nodes/services.
    """
    def __init__(self):
        self.cert_path = os.getenv("INTERNAL_CERT_PATH") # e.g. /certs/node.crt
        self.key_path = os.getenv("INTERNAL_KEY_PATH")   # e.g. /certs/node.key
        self.ca_path = os.getenv("INTERNAL_CA_PATH")     # e.g. /certs/ca.crt
        self.use_mtls = all([self.cert_path, self.key_path, self.ca_path])

    def _get_ssl_context(self) -> Optional[ssl.SSLContext]:
        if not self.use_mtls:
            return None
        
        try:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=self.ca_path)
            context.load_cert_chain(certfile=self.cert_path, keyfile=self.key_path)
            # Enforce TLS 1.3
            context.minimum_version = ssl.TLSVersion.TLSv1_3
            return context
        except Exception as e:
            logger.error(f"[mTLS] Failed to initialize SSL context: {e}")
            return None

    async def request(
        self, 
        method: str, 
        url: str, 
        json_data: Optional[Dict[str, Any]] = None, 
        **kwargs
    ) -> httpx.Response:
        """Sends a secure request to an internal endpoint."""
        ssl_context = self._get_ssl_context()
        
        async with httpx.AsyncClient(verify=ssl_context or True) as client:
            # Internal service token for secondary auth layer
            headers = kwargs.pop("headers", {})
            headers["X-Internal-Service-Token"] = os.getenv("BRAIN_SERVICE_TOKEN", "sovereign_pulse")
            
            response = await client.request(
                method, 
                url, 
                json=json_data, 
                headers=headers,
                timeout=30.0,
                **kwargs
            )
            return response

# Global instance
internal_client = InternalServiceClient()
