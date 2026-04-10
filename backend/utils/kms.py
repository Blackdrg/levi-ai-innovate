"""
Sovereign KMS Interface v14.1.0.
Cloud-agnostic Key Management System (Generic Interface).
Default Backend: HashiCorp Vault.
Fallback Backend: Local Environment (PBKDF2).
"""

import os
import logging
import abc
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

class GenericKMS(abc.ABC):
    """
    Abstract Base Class for KMS providers.
    Ensures LEVI remains cloud-agnostic.
    """
    @abc.abstractmethod
    def encrypt_dek(self, dek: bytes, key_id: str = "default") -> bytes:
        """Encrypts a Data Encryption Key (DEK)."""
        pass

    @abc.abstractmethod
    def decrypt_dek(self, enc_dek: bytes, key_id: str = "default") -> bytes:
        """Decrypts a Data Encryption Key (DEK)."""
        pass

class VaultKMSAdapter(GenericKMS):
    """
    HashiCorp Vault Adapter (Transit Engine).
    Production recommendation for self-hosted sovereign clouds.
    """
    def __init__(self, addr: Optional[str] = None, token: Optional[str] = None):
        self.addr = addr or os.getenv("VAULT_ADDR", "http://localhost:8200")
        self.token = token or os.getenv("VAULT_TOKEN")
        self.mount = os.getenv("VAULT_TRANSIT_MOUNT", "transit")

    def encrypt_dek(self, dek: bytes, key_id: str = "default") -> bytes:
        import base64
        if not self.token:
            logger.error("[KMS] Vault Token missing. Falling back to LocalKMS.")
            return LocalKMSAdapter().encrypt_dek(dek, key_id)
            
        try:
            url = f"{self.addr}/v1/{self.mount}/encrypt/{key_id}"
            headers = {"X-Vault-Token": self.token}
            payload = {"plaintext": base64.b64encode(dek).decode()}
            
            with httpx.Client(timeout=5.0) as client:
                res = client.post(url, json=payload, headers=headers)
                res.raise_for_status()
                ciphertext = res.json()["data"]["ciphertext"]
                return ciphertext.encode()
        except Exception as e:
            logger.error(f"[KMS] Vault Encryption Failure: {e}")
            raise

    def decrypt_dek(self, enc_dek: bytes, key_id: str = "default") -> bytes:
        import base64
        if not self.token:
            return LocalKMSAdapter().decrypt_dek(enc_dek, key_id)
            
        try:
            url = f"{self.addr}/v1/{self.mount}/decrypt/{key_id}"
            headers = {"X-Vault-Token": self.token}
            payload = {"ciphertext": enc_dek.decode()}
            
            with httpx.Client(timeout=5.0) as client:
                res = client.post(url, json=payload, headers=headers)
                res.raise_for_status()
                plaintext_b64 = res.json()["data"]["plaintext"]
                return base64.b64decode(plaintext_b64)
        except Exception as e:
            logger.error(f"[KMS] Vault Decryption Failure: {e}")
            raise

class LocalKMSAdapter(GenericKMS):
    """
    Local PBKDF2 Adapter.
    Uses SYSTEM_SECRET to derive master keys. Good for air-gapped dev.
    """
    def __init__(self):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        self.secret = os.getenv("SYSTEM_SECRET", "levi-default-0000").encode()
        self.salt = b'sovereign_local_kms_v1'

    def _derive_key(self) -> bytes:
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        import base64
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.secret))

    def encrypt_dek(self, dek: bytes, key_id: str = "default") -> bytes:
        from cryptography.fernet import Fernet
        f = Fernet(self._derive_key())
        return f.encrypt(dek)

    def decrypt_dek(self, enc_dek: bytes, key_id: str = "default") -> bytes:
        from cryptography.fernet import Fernet
        f = Fernet(self._derive_key())
        return f.decrypt(enc_dek)

def get_kms_provider() -> GenericKMS:
    """Factory to get the configured KMS provider."""
    provider_type = os.getenv("KMS_PROVIDER", "local").lower()
    if provider_type == "vault":
        return VaultKMSAdapter()
    return LocalKMSAdapter()
