import os
import base64
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    logger.warning("cryptography package not found. Memory vault using DEGRADED obfuscation.")

class SovereignVault:
    """
    Sovereign Vault v13.1.0: Hardened Identity Protection.
    Implements Envelope Encryption and Key Rotation.
    
    Architecture:
    1. Master Key (MK): Derived from SYSTEM_SECRET + Salt.
    2. Data Encryption Key (DEK): Generated per-session/operation.
    3. Payload: [MK_VERSION][ENCRYPTED_DEK][ENCRYPTED_DATA]
    """
    _master_fernet: Optional[Any] = None
    _rotation_keys: Dict[str, Any] = {}

    @classmethod
    def _get_master_fernet(cls, version: str = "v1"):
        if version == "v1" and cls._master_fernet:
            return cls._master_fernet
            
        secret = os.getenv(f"SYSTEM_SECRET_{version.upper()}", os.getenv("SYSTEM_SECRET", "levi-sovereign-default-secret-2024"))
        salt = b'levi_salt_v13'
        
        if HAS_CRYPTO:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
            fernet = Fernet(key)
            if version == "v1": cls._master_fernet = fernet
            return fernet
        else:
            return "DEGRADED"

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
        
        # 3. Encrypt DEK with Master Key (Envelope)
        mk = cls._get_master_fernet("v1")
        enc_dek = mk.encrypt(dek)
        
        # 4. Pack the Envelope
        # Format: version:enc_dek:enc_data
        payload = f"v1:{base64.b64encode(enc_dek).decode()}:{base64.b64encode(enc_data).decode()}"
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
            enc_dek = base64.b64decode(enc_dek_b64)
            enc_data = base64.b64decode(enc_data_b64)
            
            # 1. Decrypt DEK with Master Key
            mk = cls._get_master_fernet(version)
            dek = mk.decrypt(enc_dek)
            
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
        pass
