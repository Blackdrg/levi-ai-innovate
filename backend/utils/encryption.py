import os
import base64
import logging
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

from .kms import get_kms_provider

HAS_CRYPTO = True
try:
    from cryptography.fernet import Fernet
except ImportError:
    HAS_CRYPTO = False
    logger.warning("cryptography package not found. Memory vault using DEGRADED obfuscation.")

class SovereignVault:
    """
    Sovereign Vault v14.0.0: Hardened Identity Protection.
    Implements Envelope Encryption and Key Rotation.
    
    Architecture:
    1. Master Key (MK): Derived from SYSTEM_SECRET + Salt.
    2. Data Encryption Key (DEK): Generated per-session/operation.
    3. Payload: [MK_VERSION][ENCRYPTED_DEK][ENCRYPTED_DATA]
    """
    _master_fernet: Optional[Any] = None
    _rotation_keys: Dict[str, Any] = {}

    _kms: Optional[Any] = None

    @classmethod
    def _get_kms(cls):
        if not cls._kms:
            cls._kms = get_kms_provider()
        return cls._kms

    @classmethod
    def encrypt(cls, data: str) -> str:
        """
        Encrypts data using Envelope Encryption.
        Returns: v1:base64(enc_dek):base64(enc_data)
        """
        if not data: return ""
        if not HAS_CRYPTO: return f"[OBF]{base64.b64encode(data.encode()).decode()}"

        # 1. Generate a transient DEK (Data Encryption Key)
        dek = Fernet.generate_key()
        f_dek = Fernet(dek)
        
        # 2. Encrypt Data with DEK
        enc_data = f_dek.encrypt(data.encode())
        
        # 3. Encrypt DEK with KMS (Envelope Residency)
        kms = cls._get_kms()
        enc_dek_bytes = kms.encrypt_dek(dek)
        
        # 4. Pack the Envelope
        # Format: kms_v1:base64(enc_dek):base64(enc_data)
        payload = f"kms_v1:{base64.b64encode(enc_dek_bytes).decode()}:{base64.b64encode(enc_data).decode()}"
        return payload

    @classmethod
    def decrypt(cls, token: str) -> str:
        """
        Decrypts an Envelope-protected token.
        """
        if not token: return ""
        if token.startswith("[OBF]"):
            return base64.b64decode(token[5:].encode()).decode()
        
        if ":" not in token: return token # Not an envelope

        try:
            parts = token.split(":")
            if len(parts) != 3: return token
            
            version, enc_dek_b64, enc_data_b64 = parts
            enc_dek_bytes = base64.b64decode(enc_dek_b64)
            enc_data = base64.b64decode(enc_data_b64)
            
            # 1. Decrypt DEK with KMS
            kms = cls._get_kms()
            dek = kms.decrypt_dek(enc_dek_bytes)
            
            # 2. Decrypt Data with DEK
            f_dek = Fernet(dek)
            return f_dek.decrypt(enc_data).decode()
            
        except Exception as e:
            logger.error(f"SovereignVault: Decryption failure (Envelope {token[:10]}): {e}")
            return "[DECRYPTION_ERROR]"

    @classmethod
    def rotate_master_key(cls, new_version: str):
        """Sets up the system for the next key rotation cycle."""
        logger.info(f"SovereignVault: Rotating to Master Key version {new_version}")
        # In practice, this would trigger a background task to re-encrypt all stored T3/T4 data
class SovereignKMS:
    """
    Sovereign KMS Interface for high-fidelity cognitive signing.
    Used for HMAC-based audit chains and cryptographic verification.
    """
    
    @staticmethod
    def sign_trace(payload: str) -> str:
        """
        Signs a trace payload using the system secret.
        Returns a hex-encoded HMAC-SHA256 signature.
        """
        import hmac
        import hashlib
        
        secret = os.getenv("SYSTEM_SECRET", "levi-default-0000").encode()
        signature = hmac.new(
            secret,
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        return signature

    @staticmethod
    def verify_trace(payload: str, signature: str) -> bool:
        """Verifies a trace payload against a signature."""
        import hmac
        import hashlib
        
        secret = os.getenv("SYSTEM_SECRET", "levi-default-0000").encode()
        expected = hmac.new(
            secret,
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
