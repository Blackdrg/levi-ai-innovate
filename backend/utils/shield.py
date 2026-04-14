import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Basic PII Identification Patterns
PII_PATTERNS = {
    "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "phone": r"\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}",
    "ssn": r"\d{3}-\d{2}-\d{4}",
    "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
    "iban": r"[A-Z]{2}\d{2}[A-Z\d]{12,30}",
    "jwt": r"eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*",
    "api_key": r"(?:api_key|secret|token|password)[^a-zA-Z0-9][a-zA-Z0-9]{16,}"
}

class SovereignShield:
    """
    Sovereign Shield v8 Security Layer.
    Protects user PII before it leaves the local execution boundary.
    """

    @staticmethod
    def mask_pii(text: str) -> str:
        """
        Identifies and masks sensitive data using non-destructive placeholders.
        """
        if not text:
            return text
        
        masked_text = text
        for label, pattern in PII_PATTERNS.items():
            matches = re.findall(pattern, masked_text)
            if matches:
                logger.debug(f"[SovereignShield] Masking {len(matches)} {label}(s)")
                masked_text = re.sub(pattern, f"[MASKED_{label.upper()}]", masked_text)
        
        return masked_text

    @staticmethod
    def encrypt_pulse(payload: dict, secret: str, aad: str = "") -> str:
        """
        Sovereign v15.0 GA: AES-256-GCM Pulse Encryption with AAD.
        Ensures inter-node mission data is private and bound to its metadata.
        """
        import json
        import base64
        import hashlib
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import os

        # Derive a 32-byte key from the DCN secret
        key = hashlib.sha256(secret.encode()).digest()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        
        data = json.dumps(payload).encode()
        # Bind the AAD to the ciphertext
        ciphertext = aesgcm.encrypt(nonce, data, aad.encode() if aad else None)
        
        # Format: base64(nonce + ciphertext)
        return base64.b64encode(nonce + ciphertext).decode()

    @staticmethod
    def decrypt_pulse(encrypted_data: str, secret: str, aad: str = "") -> dict:
        """
        Sovereign v15.0 GA: AES-256-GCM Pulse Decryption with AAD verification.
        """
        import json
        import base64
        import hashlib
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        try:
            key = hashlib.sha256(secret.encode()).digest()
            aesgcm = AESGCM(key)
            raw = base64.b64decode(encrypted_data)
            
            nonce = raw[:12]
            ciphertext = raw[12:]
            
            decrypted = aesgcm.decrypt(nonce, ciphertext, aad.encode() if aad else None)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"[Shield] Decryption failure: {e}")
            return {}

import hashlib
