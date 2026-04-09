"""
LEVI-AI Sovereign Fast-Path Router v14.1.
Intercepts low-complexity queries to bypass heavy DAG orchestration.
Target Latency: < 2s.
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple

from .orchestrator_types import IntentResult, BrainMode, EngineRoute
from backend.utils.llm_utils import call_lightweight_llm

logger = logging.getLogger(__name__)

class FastPathRouter:
    """
    Ultra-fast decision layer.
    Rules:
    1. Greeting/Chat intent + High Confidence -> Fast Path.
    2. Exact Cache Match (Phase 2) -> Fast Path.
    3. Low Complexity Score (<0.3) -> Fast Path.
    """

    FAST_INTENTS = {"greeting", "chat", "joke", "thanks"}
    COMPLEXITY_THRESHOLD = 0.3
    CONFIDENCE_THRESHOLD = 0.9

    @classmethod
    async def try_fast_route(
        cls, 
        user_input: str, 
        intent: IntentResult,
        user_id: str,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Attempts to resolve the query via the fast path.
        Returns None if the query requires heavy pipeline escalation.
        """
        start_time = time.time()
        
        # 0. T1 Cache Check (v14.1)
        from backend.services.cache_manager import CacheManager
        cached = await CacheManager.get_response(user_input)
        if cached:
            return cached

        # 1. Evaluate Eligibility
        is_fast_intent = intent.intent_type in cls.FAST_INTENTS
        is_low_complexity = intent.complexity_level <= 1 # Scale 0-3
        is_high_confidence = intent.confidence_score >= cls.CONFIDENCE_THRESHOLD
        
        # Override for forced mode
        # If user explicitly wants DEEP, we don't fast-path
        
        can_fast_path = (is_fast_intent and is_high_confidence) or (is_low_complexity and is_high_confidence)
        
        if not can_fast_path:
            return None

        logger.info(f"[FastPath] Routing pulse detected for intent: {intent.intent_type}")

        # 2. Execution (Lightweight LLM or Template)
        # TODO: Add Cache Check here in Phase 2
        
        messages = [
            {"role": "system", "content": "You are LEVI, a helpful and efficient sovereign AI. Keep your response concise (max 3 sentences) as we are in Fast Mode."},
            {"role": "user", "content": user_input}
        ]
        
        try:
            response_text = await call_lightweight_llm(messages)
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                "response": response_text,
                "request_id": f"fast_{int(time.time())}",
                "mode": BrainMode.FAST.value,
                "route": EngineRoute.LOCAL.value,
                "latency_total": latency_ms,
                "intent": intent.intent_type,
                "status": "success",
                "fast_path": True
            }
        except Exception as e:
            logger.error(f"[FastPath] Execution failure: {e}")
            return None # Escalate to heavy pipeline on failure
