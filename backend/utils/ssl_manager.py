"""
Sovereign SSL & Certificate Manager (v16.1).
Handles the loading and verification of mTLS certificates for LEVI inter-node communication.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SSLManager:
    CERT_PATH = os.getenv("CERT_PATH", "backend/certs/dcn")
    
    @classmethod
    def get_server_credentials(cls) -> Optional[tuple]:
        """Loads certs for the gRPC Server side."""
        try:
            with open(os.path.join(cls.CERT_PATH, "server.key"), "rb") as f:
                private_key = f.read()
            with open(os.path.join(cls.CERT_PATH, "server.crt"), "rb") as f:
                certificate_chain = f.read()
            with open(os.path.join(cls.CERT_PATH, "ca.crt"), "rb") as f:
                root_certificates = f.read()
                
            return (private_key, certificate_chain, root_certificates)
        except FileNotFoundError:
            logger.warning("⚠️ [SSL] Local mTLS certificates not found. Falling back to insecure.")
            return None

    @classmethod
    def get_client_credentials(cls) -> Optional[tuple]:
        """Loads certs for the gRPC Client side."""
        try:
            with open(os.path.join(cls.CERT_PATH, "client.key"), "rb") as f:
                private_key = f.read()
            with open(os.path.join(cls.CERT_PATH, "client.crt"), "rb") as f:
                certificate_chain = f.read()
            with open(os.path.join(cls.CERT_PATH, "ca.crt"), "rb") as f:
                root_certificates = f.read()
                
            return (private_key, certificate_chain, root_certificates)
        except FileNotFoundError:
            logger.warning("⚠️ [SSL] Local mTLS certificates not found. Falling back to insecure.")
            return None

    @classmethod
    def generate_placeholder_certs(cls):
        """Generates self-signed certs for local dev testing if they don't exist."""
        # For a truly autonomous system, we'd use 'cryptography' to generate these if missing.
        # In this task, we assume the user provides them or the CI/CD pipeline injects them.
        pass
