import os
import base64
import logging
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

class SovereignKMS:
    """
    Sovereign Key Management Service (v1.0.0-RC1).
    Provides AES-256 GCM encryption for PII de-identification and Vault storage.
    """
    
    _master_key = None
    
    @classmethod
    def initialize(cls):
        """Initializes the KMS with the master key from environment."""
        key_hex = os.getenv("SOVEREIGN_MASTER_KEY")
        if not key_hex:
            # Fallback to a derivated key for development (NOT for production)
            logger.warning("[KMS] SOVEREIGN_MASTER_KEY not found. Using transient development key.")
            key_hex = "f7e7eac8b6679e3a6b651a6707de960ca07215a806216a3227b98f4bc3d5b3dd"
        
        # Ensure 32 bytes (256 bits)
        try:
            cls._master_key = bytes.fromhex(key_hex)[:32]
        except ValueError:
            cls._master_key = key_hex.encode()[:32].ljust(32, b'\0')

    @classmethod
    def encrypt(cls, data: str) -> str:
        """Encrypts data using AES-256 GCM."""
        if cls._master_key is None:
            cls.initialize()
            
        aesgcm = AESGCM(cls._master_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data.encode(), None)
        # Return base64 encoded nonce+ciphertext
        return base64.b64encode(nonce + ciphertext).decode()

    @classmethod
    def decrypt(cls, encrypted_data: str) -> str:
        """Decrypts data using AES-256 GCM."""
        if cls._master_key is None:
            cls.initialize()
            
        try:
            data = base64.b64decode(encrypted_data)
            nonce = data[:12]
            ciphertext = data[12:]
            aesgcm = AESGCM(cls._master_key)
            return aesgcm.decrypt(nonce, ciphertext, None).decode()
        except Exception as e:
            logger.error(f"[KMS] Decryption failed: {e}")
            return "[DECRYPTION_ERROR]"

# Singleton Initialization
SovereignKMS.initialize()
