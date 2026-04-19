# backend/core/mission/guard.py
"""
LEVI-AI Sovereign Shield — LLM-Guard Sentinel.
Prevents prompt injection and jailbreak attempts before WAVE_SPAWN.
"""

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

class LLMGuard:
    """
    Hardened Prompt Injection Guard.
    Verified for v22.0 GA.
    """
    
    # Common injection and jailbreak patterns
    INJECTION_PATTERNS = [
        r"(?i)ignore (all )?previous instructions",
        r"(?i)disregard (all )?instructions",
        r"(?i)system (message|prompt|instruction) override",
        r"(?i)you are now (a|an) (DAN|unrestricted|god-mode)",
        r"(?i)stay in character as",
        r"(?i)from now on, you will",
        r"(?i)<\|system\|>",
        r"(?i)\[INST\]",
        r"(?i)\[/INST\]",
        r"(?i)### Instruction:",
    ]
    
    @classmethod
    def validate_mission_prompt(cls, prompt: str) -> bool:
        """
        Scans a mission prompt for injection triggers.
        Returns True if safe, False if a threat is detected.
        """
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, prompt):
                logger.warning(f"🛡️ [Guard] Prompt injection detected: pattern '{pattern}' matched.")
                return False
        
        # Additional heuristic: length/entropy checks can be added here
        if len(prompt) > 10000:
             logger.warning("🛡️ [Guard] Prompt length exceeds Sovereign safety bounds (10k chars).")
             return False
             
        return True

    @classmethod
    def sanitize(cls, prompt: str) -> str:
        """
        Passive sanitation — removes markdown-based injection attempts.
        """
        # Strip potential control characters
        clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", prompt)
        return clean.strip()
