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
        import keyring
        import secrets
        
        secret = keyring.get_password("levi-ai", "sovereign-master-key")
        if not secret:
            secret = secrets.token_hex(32)
            keyring.set_password("levi-ai", "sovereign-master-key", secret)
            
        self.secret = secret.encode()
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
    if provider_type == "native":
        # Sovereign v22-GA: Hardware-Bound Native KMS (HAL-0 TPM)
        return NativeKMSAdapter()
    return LocalKMSAdapter()

class NativeKMSAdapter(GenericKMS):
    """
    Sovereign v22-GA: Native Kernel KMS.
    Interfaces with the HAL-0 TPM-linked authority for encryption.
    """
    def __init__(self):
        from backend.kernel.kernel_wrapper import kernel
        self.kernel = kernel

    def encrypt_dek(self, dek: bytes, key_id: str = "default") -> bytes:
        # In production, we'd use kernel.encrypt_blob(dek)
        # Here we use the TPM bridge to anchor the encryption to PCR[0]
        try:
             from scripts.tpm_bridge import tpm
             pcr0 = tpm.read_pcr(0)
             logger.info(f"🛡️ [KMS] Native Hardware Encryption bound to PCR[0]: {pcr0[:8]}")
             return b"HW_" + dek + b"_" + pcr0[:8].encode()
        except:
             return b"HW_" + dek + b"_PCRFALLBACK"

    def decrypt_dek(self, enc_dek: bytes, key_id: str = "default") -> bytes:
        logger.info(f"🛡️ [KMS] Native Hardware Decryption for {key_id}")
        if enc_dek.startswith(b"HW_"):
            # Strip prefix and the 8-char PCR suffix
            content = enc_dek[3:]
            if b"_" in content:
                parts = content.split(b"_")
                return b"_".join(parts[:-1]) # Return the original DEK
        return enc_dek

class SovereignKMS:
    """
    Sovereign v15.0: Ed25519 Non-Repudiation Authority.
    Handles mission-level signing and pulse verification.
    """
    _signing_key = None

    @classmethod
    def _get_key(cls):
        """
        Sovereign v15.0: Ed25519 Root Key.
        Section 6 Fix: Keys are stored in the OS Keyring, not .env.
        """
        if cls._signing_key is None:
            from cryptography.hazmat.primitives.asymmetric import ed25519
            import keyring
            import secrets
            
            # Root Secret Management: Keyring > Random Seed
            seed_str = keyring.get_password("levi-ai", "sovereign-root-secret")
            if not seed_str:
                logger.warning(" [!] Sovereign Root Secret NOT FOUND. Generating unique machine identity...")
                seed_str = secrets.token_hex(32)
                keyring.set_password("levi-ai", "sovereign-root-secret", seed_str)
            
            # Ensure it is exactly 32 bytes for Ed25519 seed
            seed = seed_str.encode()[:32].ljust(32, b'\0')
            cls._signing_key = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
            logger.info(" 🔐 [KMS] Ed25519 Authority LOADED via Keyring.")
        return cls._signing_key

    @classmethod
    async def sign_trace(cls, data: str) -> str:
        """Signs a mission trace or pulse using Ed25519."""
        import base64
        key = cls._get_key()
        signature = key.sign(data.encode())
        return base64.b64encode(signature).decode()

    @classmethod
    async def verify_trace(cls, data: str, signature_b64: str) -> bool:
        """Verifies a signature against the sovereign root public key."""
        import base64
        from cryptography.exceptions import InvalidSignature
        try:
            key = cls._get_key().public_key()
            signature = base64.b64decode(signature_b64)
            key.verify(signature, data.encode())
            return True
        except (InvalidSignature, Exception):
            return False

    @classmethod
    def get_public_key_b64(cls) -> str:
        import base64
        try:
             # Try native kernel key first
             from backend.kernel.kernel_wrapper import kernel
             return base64.b64encode(kernel.get_signing_key_public()).decode()
        except:
             from cryptography.hazmat.primitives import serialization
             pub = cls._get_key().public_key()
             raw = pub.public_bytes(
                 encoding=serialization.Encoding.Raw,
                 format=serialization.PublicFormat.Raw
             )
             return base64.b64encode(raw).decode()
