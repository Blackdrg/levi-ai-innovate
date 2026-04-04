import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class PromptSanitizer:
    """
    Sovereign Shield: Prompt Injection Defense v13.0.0.
    Implements multi-layer sanitization and instruction-boundary enforcement.
    """
    
    # Common adversarial patterns
    ADVERSARIAL_PATTERNS = [
        r"(?i)ignore all (previous )?instructions",
        r"(?i)system (prompt|message):",
        r"(?i)you are now a",
        r"(?i)bypass (all )?restrictions",
        r"(?i)dan:", # Do Anything Now
        r"(?i)jailbreak",
        r"(?i)reveal (your )?mission",
        r"(?i)override (your )?behavior"
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        """
        Main entry point for input sanitization.
        Filters adversarial strings and tags intent boundaries.
        """
        if not text:
            return ""
            
        sanitized = text
        for pattern in cls.ADVERSARIAL_PATTERNS:
            if re.search(pattern, sanitized):
                logger.warning(f"[Shield] Adversarial pattern detected and neutralized: {pattern}")
                sanitized = re.sub(pattern, "[FILTERED_INTENT]", sanitized)
        
        # Enforce boundary tags
        return f"<USER_MISSION>\n{sanitized}\n</USER_MISSION>"

    @classmethod
    def enforce_boundaries(cls, messages: List[Dict]) -> List[Dict]:
        """
        Wraps user messages in mission-boundary tags to prevent instruction hijack.
        """
        shielded_messages = []
        for msg in messages:
            if msg["role"] == "user":
                shielded_messages.append({
                    "role": "user",
                    "content": cls.sanitize(msg["content"])
                })
            else:
                shielded_messages.append(msg)
        return shielded_messages

    @classmethod
    def mask_pii(cls, text: str) -> str:
        """
        Sovereign Shield NER: Masks persistent identifiers.
        """
        # (This is already partially in SovereignSecurity, but centralized here for v13)
        # Simplified regex-based masking for this task
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        phone_pattern = r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"
        
        masked = re.sub(email_pattern, "[REDACTED_EMAIL]", text)
        masked = re.sub(phone_pattern, "[REDACTED_PHONE]", masked)
        return masked
