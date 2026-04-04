import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class SovereignSecurity:
    """
    Implements PII masking and prompt injection detection for all Sovereign engines.
    """
    
    PII_PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\+?(\d{1,3})?[-. ]?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}",
        "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "location": r"\b[0-9]{1,5}\s(?:[A-Z][a-z]+\s*)+(?:Ave|St|Rd|Blvd|Ln|Ct|Oaks|Way|Circle|Dr)\b|\b[A-Z][a-z]+,\s[A-Z]{2}\s[0-9]{5}\b",
        "name": r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b", # Two-word proper names (basic NER)
        "org": r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\s(?:Inc|Corp|LLC|Ltd|Org)\b"
    }

    _DEIDENTIFICATION_MAP = {} # In-memory cache for session persistence

    @classmethod
    def mask_pii(cls, text: str, user_id: str = "global") -> str:
        """
        Sovereign Shield v9.8.1: Advanced PII Redaction.
        Finds and masks PII using high-fidelity regex (NER-Lite).
        """
        return cls.deidentify(text, user_id)

    @classmethod
    def deidentify(cls, text: str, user_id: str) -> str:
        """
        Replaces sensitive facts with persistent placeholders.
        Example: 'John Doe lives in New York' -> '[NAME_M_1] lives in [LOC_M_1]'
        """
        masked_text = text
        for pii_type, pattern in cls.PII_PATTERNS.items():
            matches = list(re.finditer(pattern, masked_text))
            for match in reversed(matches):
                raw_val = match.group()
                # Create a persistent hash for this user/value pair
                import hashlib
                val_hash = hashlib.md5(f"{user_id}:{raw_val}".encode()).hexdigest()[:4]
                placeholder = f"[{pii_type.upper()}_{val_hash}]"
                
                start, end = match.span()
                masked_text = masked_text[:start] + placeholder + masked_text[end:]
        
        return masked_text

    @classmethod
    def detect_injection(cls, query: str) -> bool:
        """Basic detection of system prompt injection attempts."""
        patterns = [
            r"ignore previous instructions",
            r"you are now",
            r"system override",
            r"reveal your system prompt",
            r"disregard all earlier"
        ]
        q_lower = query.lower()
        for p in patterns:
            if re.search(p, q_lower):
                logger.warning(f"Malicious prompt injection attempt detected: {query[:50]}")
                return True
        return False
