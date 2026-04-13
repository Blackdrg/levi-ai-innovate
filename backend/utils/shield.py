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
    def demask_pii(text: str, original_map: Dict[str, str]) -> str:
        """
        Optional: Restores original values (for internal history/persistence).
        """
        # Logic for maintaining a local demasking map if needed in Phase 8
        return text
