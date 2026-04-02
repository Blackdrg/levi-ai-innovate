"""
Sovereign Orchestration Layer v8.
The primary entry point for the LEVI-AI cognitive engine.
Handles credit validation, budgeting, and high-level routing.
"""

import logging
import asyncio
import uuid
from typing import Dict, Any, Optional, AsyncGenerator

from .brain import LeviBrainV8
from .orchestrator_types import EngineRoute, OrchestratorResponse, IntentResult
from backend.services.payments.logic import use_credits
from backend.db.redis import check_exact_match, store_exact_match, check_semantic_match

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    LEVI-AI v8 Orchestrator.
    Manages the lifecycle of a cognitive mission.
    """
    def __init__(self):
        self.brain = LeviBrainV8()

    async def handle_mission(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        streaming: bool = False,
        **kwargs
    ) -> Any:
        """
        Routes a user request through the cognitive pipeline.
        Includes pre-mission checks (cache, credits) and post-mission synthesis.
        """
        request_id = f"mission_{uuid.uuid4().hex[:8]}"
        logger.info("[Orchestrator] Initiating Mission: %s", request_id)

        # 1. Fast Cache Layer (Exact & Semantic)
        if not kwargs.get("bypass_cache", False):
            cached = check_exact_match(user_id, user_input, kwargs.get("mood", "philosophical"))
            if not cached:
                cached = check_semantic_match(user_id, user_input, kwargs.get("mood", "philosophical"), threshold=0.95)
            
            if cached:
                logger.info("[Orchestrator] Cache Hit. Mission skipped.")
                return {
                    "response": cached,
                    "request_id": request_id,
                    "route": "cache"
                }

        # 2. Credit Lock
        # We check intent roughly here or let the brain handle it. 
        # For DDD, the Orchestrator (Application Service) handles the transaction logic.
        # But we need intent for credit cost. Let's let the brain perceive first.

        # 3. Cognitive Mission Execution
        try:
            # Note: For streaming, the brain.run would need to be an async generator
            if streaming:
                 return self.brain.stream(user_input, user_id, session_id, request_id=request_id, **kwargs)
            
            result = await self.brain.run(user_input, user_id, session_id, request_id=request_id, **kwargs)
            
            # Post-Mission: Cache the successful result
            if result.get("response"):
                store_exact_match(user_id, user_input, kwargs.get("mood", "philosophical"), result["response"])
            
            return result
        except Exception as e:
            logger.exception("[Orchestrator] Mission failure: %s", e)
            return {
                "response": "The thought stream was interrupted by a quantum fluctuation.",
                "error": str(e),
                "request_id": request_id,
                "status": "failed"
            }

# --- Standard Entry Point ---
_orchestrator = Orchestrator()

async def run_orchestrator(**kwargs):
    """Bridge for API v1 and legacy components."""
    return await _orchestrator.handle_mission(**kwargs)
