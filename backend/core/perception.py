"""
Sovereign Perception Layer v8.
Extracts intent, entities, emotion, and context from user input.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from .planner import detect_intent
from backend.memory.manager import MemoryManager
from backend.utils.shield import SovereignShield


logger = logging.getLogger(__name__)

class PerceptionEngine:
    def __init__(self, memory: MemoryManager):
        self.memory = memory

    async def perceive(self, user_input: str, user_id: str, session_id: str, **kwargs) -> Dict[str, Any]:
        """
        Synthesizes raw input into a structured cognitive perception.
        Combines 4-tier memory context with real-time intent detection.
        """
        # 0. Sovereign Shield: PII Masking (Security Layer)
        safe_input = SovereignShield.mask_pii(user_input)
        if safe_input != user_input:
            logger.info("[Perception] Sovereign Shield: Sensitive data masked.")

        # 1. Intent & Complexity Analysis
        intent = await detect_intent(safe_input)

        
        # 2. Context Hydration (4-Tier Memory)
        context = await self.memory.get_combined_context(user_id, session_id, user_input)
        context.update(kwargs)
        
        return {
            "input": safe_input,
            "raw_input": user_input, # Maintain original internally for context

            "intent": intent,
            "context": context,
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
