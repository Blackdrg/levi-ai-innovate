# backend/core/security/redactor.py
import re
import logging
from typing import List

logger = logging.getLogger("Redactor")

class PIIRedactor:
    """
    Sovereign v22.1: Forensic PII Scrubber.
    Section 97 Compliance.
    Handles redaction of sensitive patterns before data leaves the sovereign boundary.
    """
    
    # Standard PII Patterns (Prioritized: Secrets first to avoid numeric collisions)
    PATTERNS = [
        # API Keys / Secrets (Common headers) - Move to top
        (r"(?i)(api[_-]?key|secret|password|token)[\s:=]+[a-zA-Z0-9_\-\.]{16,}", r"\1: [SECRET_REDACTED]"),
        # Fixed-format API Keys (e.g., Stripe/OpenAI)
        (r"\b(sk_[a-z0-9]{20,}|AIza[a-z0-9_\\\-]{35})\b", "[SECRET_REDACTED]"),
        # Email
        (r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL_REDACTED]"),
        # IPv4
        (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP_REDACTED]"),
        # Credit Card (Basic)
        (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CARD_REDACTED]"),
        # Phone (Narrowed to avoid matching parts of secrets)
        (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_REDACTED]"),
        # SSN (US)
        (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
    ]

    @classmethod
    def scrub(cls, text: str) -> str:
        """
        Scrub PII from text using the predefined pattern matrix.
        Returns the sanitized string.
        """
        if not text: return text
        
        scrubbed = text
        for pattern, replacement in cls.PATTERNS:
            scrubbed = re.sub(pattern, replacement, scrubbed)
            
        if scrubbed != text:
            logger.info("🛡️ [Forensics] PII markers detected and scrubbed from mission stream.")
            
        return scrubbed

    @classmethod
    def scrub_batch(cls, texts: List[str]) -> List[str]:
        return [cls.scrub(t) for t in texts]
