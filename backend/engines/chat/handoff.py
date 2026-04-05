"""
Sovereign Neural Handoff v13.0.0.
Absolute Monolith Dynamic Provider Routing (Local vs. Cloud).
Hardened for Adaptive Pulse v4.1 (Binary/zlib) and identity-aware context.
"""

import logging
import re
import os
from typing import Dict, Any, Optional
from backend.services.local_llm import local_llm
from backend.broadcast_utils import SovereignBroadcaster

logger = logging.getLogger(__name__)

class SovereignHandoff:
    """
    Sovereign Hybrid Controller (v13.0.0).
    Optimizes for Privacy, Intelligence, and Speed.
    """
    
    # Sensitivity Patterns (Implicit PII or High Privacy Context)
    SENSITIVE_PATTERNS = [
        r"password", r"secret", r"private key", r"bank", r"medical",
        r"health", r"financial", r"tax", r"ssn", r"identity",
        r"passport", r"credit card", r"cvv", r"pin code", r"auth token"
    ]

    @classmethod
    def analyze_mission(cls, prompt: str, task_type: str = "chat") -> Dict[str, Any]:
        """Analyzes a mission for the v13.0.0 Absolute Monolith."""
        prompt_lower = prompt.lower()
        word_count = len(prompt.split())
        
        is_sensitive = any(re.search(p, prompt_lower) for p in cls.SENSITIVE_PATTERNS)
        is_complex = word_count > 300 or task_type in ["research", "code_architect"]
        is_latency_critical = task_type in ["chat", "fast_reply"]
        
        return {
            "sensitive": is_sensitive,
            "complex": is_complex,
            "latency_critical": is_latency_critical,
            "word_count": word_count
        }

    @classmethod
    def select_provider(cls, analysis: Dict[str, Any], user_id: str = "guest") -> str:
        """
        Sovereign Routing logic (v13.0.0):
        1. OFFLINE OVERRIDE: Force ALL to local.
        2. Privacy Override: Local Immunity.
        3. Local Availability: Efficiency matching.
        4. Cloud Strategy: Groq/Together.
        """
        # 0. v13.0 Local Sovereignty Override
        if os.getenv("OFFLINE_MODE") == "true":
            return "local"

        provider = "groq"
        
        # 1. Privacy Override (Local Immunity)
        if analysis["sensitive"]:
            if local_llm.is_available():
                provider = "local"
            else:
                provider = "DETERMINISTIC_SAFE_MODE"
        
        # 2. Local Efficiency Check
        elif local_llm.is_available() and analysis["word_count"] < 100:
            provider = "local"
            
        # 3. Cloud Strategy
        elif analysis["complex"]:
            provider = "together"
            
        # 4. Neural Handoff Pulse (v13.0 Telemetry Sync)
        SovereignBroadcaster.broadcast({
            "type": "NEURAL_HANDOFF",
            "provider": provider,
            "sensitive": analysis["sensitive"],
            "u": user_id
        })

        return provider

# Singleton graduation
handoff = SovereignHandoff()
