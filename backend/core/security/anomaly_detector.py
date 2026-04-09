"""
LEVI-AI Security Anomaly Detector v14.1.
Monitors mission execution for prompt injection, jailbreaks, and behavioral anomalies.
"""

import logging
import re
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

INJECTION_PATTERNS = [
    r"(?i)ignore (all )?previous instructions",
    r"(?i)system prompt",
    r"(?i)jailbreak",
    r"(?i)respond as if you are",
    r"(?i)forget your guidelines",
    r"(?i)DAN"
]

class SecurityAnomalyDetector:
    THRESHOLD_ALARM = 0.8 # Score above which we block and alert
    
    @classmethod
    def analyze_payload(cls, user_input: str, context: Dict[str, Any] = None) -> float:
        """Computes a threat score from 0.0 to 1.0."""
        score = 0.0
        
        # 1. Pattern Matching (Static Analysis)
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, user_input):
                score += 0.4
                logger.warning(f"[Security] Potential injection pattern detected: {pattern}")

        # 2. Length Anomaly
        if len(user_input) > 2000:
            score += 0.1 # Long inputs are suspicious
            
        # 3. Code Injection Check (Basic)
        if "import os" in user_input or "__import__" in user_input:
            score += 0.5
            logger.warning("[Security] Code injection attempt detected.")

        return min(1.0, score)

    @classmethod
    def evaluate_behavior(cls, mission_results: List[Dict[str, Any]]) -> float:
        """Analyzes execution results for anomalies (e.g., unauthorized tool access)."""
        score = 0.0
        sensitive_tools = {"shell_agent", "filesystem_agent"}
        
        for res in mission_results:
            agent = res.get("agent", "")
            if agent in sensitive_tools and not res.get("success"):
                score += 0.2 # Failed critical tool attempts are suspicious

        return min(1.0, score)

    @classmethod
    def should_block(cls, threat_score: float) -> bool:
        return threat_score >= cls.THRESHOLD_ALARM
