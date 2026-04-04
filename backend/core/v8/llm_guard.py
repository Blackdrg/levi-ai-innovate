import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class PIIScrubber:
    """
    Sovereign Shield v9.8.1: PII Scrubber
    Masks sensitive data before any external/cloud exposure using Tokenization.
    """
    
    # Common PII Patterns
    PATTERNS = {
        "EMAIL": r"[\w\.-]+@[\w\.-]+\.\w+",
        "PHONE": r"\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b",
        "API_KEY": r"(?:sk-|ak-|ghp_)[a-zA-Z0-9]{20,}", # Generic API key patterns
        "IP": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
    }

    @classmethod
    def scrub(cls, text: str) -> str:
        """Performs tokenization-based redaction of PII."""
        scrubbed = text
        for label, pattern in cls.PATTERNS.items():
            matches = re.findall(pattern, scrubbed)
            for i, val in enumerate(list(set(matches))):
                placeholder = f"<{label}_{i+1}>"
                scrubbed = scrubbed.replace(val, placeholder)
                logger.info(f"[PIIScrubber] Masked {label} into {placeholder}.")
        return scrubbed

class LLMGuard:
    """
    LeviBrain v9.8.1: Sovereign Shield & LLM Gatekeeper.
    Enforces Brain authority by blocking LLM calls for deterministic or memory-matched tasks.
    And secures all cloud-bound neural missions.
    """

    @staticmethod
    def allow_llm(task_description: str, decision_data: Dict[str, Any]) -> bool:
        """
        Decision Logic:
        - IF internal_confidence >= 0.7: -> BLOCK LLM (Internal Match)
        - ELSE IF engine_capable == true: -> BLOCK LLM (Engine Move)
        - ELSE IF memory_match_score >= 0.7: -> BLOCK LLM (Direct Memory)
        - ELSE: -> ALLOW LLM (Neural Fallback)
        """
        internal_conf = decision_data.get("internal_conf", 0)
        engine_capable = decision_data.get("engine_capable", False)
        memory_match = decision_data.get("memory_match", 0)

        if internal_conf >= 0.7:
             logger.info(f"[LLMGuard] Blocking LLM: Internal Match High ({internal_conf}).")
             return False
             
        if engine_capable:
             logger.info(f"[LLMGuard] Blocking LLM: Engine Capability Detected.")
             return False

        if memory_match >= 0.7:
             logger.info(f"[LLMGuard] Blocking LLM: Direct Memory Match ({memory_match}).")
             return False

        logger.info(f"[LLMGuard] Allowing LLM: Neural Fallback required.")
        return True

    @staticmethod
    def secure_outbound(text: str) -> str:
        """Secure the text by scrubbing PII before external transmission."""
        return PIIScrubber.scrub(text)
