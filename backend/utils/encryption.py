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
    LEVI v6: Secure encryption vault for sensitive user memory.
    Ensures that long-term traits and preferences are stored as ciphertext in Firestore.
    """
    _fernet: Optional[Any] = None

    @classmethod
    def _get_fernet(cls):
        if cls._fernet:
            return cls._fernet
            
        secret = os.getenv("SYSTEM_SECRET", "levi-sovereign-default-secret-2024")
        salt = b'levi_salt_v6' # In production, use a unique salt per user or system
        
        if HAS_CRYPTO:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
            cls._fernet = Fernet(key)
        else:
            # Fallback to simple base64 (Not secure, but prevents crashes)
            cls._fernet = "DEGRADED"
            
        return cls._fernet

    @classmethod
    def encrypt(cls, data: str) -> str:
        """Encrypts a string into a persistent ciphertext."""
        if not data: return ""
        f = cls._get_fernet()
        
        if HAS_CRYPTO and isinstance(f, Fernet):
            return f.encrypt(data.encode()).decode()
        else:
            # Obfuscation fallback
            return f"[OBF]{base64.b64encode(data.encode()).decode()}"

    @classmethod
    def decrypt(cls, token: str) -> str:
        """Decrypts a ciphertext token back into plain text."""
        if not token: return ""
        f = cls._get_fernet()
        
        try:
            if HAS_CRYPTO and isinstance(f, Fernet):
                return f.decrypt(token.encode()).decode()
            elif token.startswith("[OBF]"):
                return base64.b64decode(token[5:].encode()).decode()
            return token # Not encrypted
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return "[DECRYPTION_ERROR]"
