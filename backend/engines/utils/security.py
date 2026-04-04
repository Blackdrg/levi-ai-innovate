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
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b"
    }

    @classmethod
    def mask_pii(cls, text: str) -> str:
        """Finds and masks PII in user queries or engine outputs."""
        masked_text = text
        for pii_type, pattern in cls.PII_PATTERNS.items():
            matches = list(re.finditer(pattern, masked_text))
            for match in reversed(matches):
                start, end = match.span()
                masked_text = masked_text[:start] + f"[{pii_type.upper()}_MASKED]" + masked_text[end:]
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
