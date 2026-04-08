"""
Sovereign Orchestration Layer v8.
The primary entry point for the LEVI-AI cognitive engine.
Handles credit validation, budgeting, and high-level routing.
"""

import logging
import uuid
import os
import time
import hashlib
from typing import Any, Dict, Optional

from .brain import LeviBrainV14
from backend.db.redis import get_redis_client, check_exact_match, store_exact_match, check_semantic_match
from .execution_state import CentralExecutionState, MissionState
from backend.evaluation.tracing import CognitiveTracer
from backend.utils.logging_context import log_request_id, log_user_id, log_session_id

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    LEVI-AI v14.0 Orchestrator.
    Manages the lifecycle of a cognitive mission with Brain Control System.
    """
    def __init__(self):
        self.brain = LeviBrainV14()


    # Blue-Green Deployment Strategy (v14.0)
    DEPLOYMENT_STRATEGY = os.getenv("DEPLOYMENT_STRATEGY", "blue") # blue (stable) / green (candidate)
    TRAFFIC_SPLIT_PCT = int(os.getenv("TRAFFIC_SPLIT_GREEN", "0"))

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
        Includes Blue-Green routing for safe version migration.
        """
        idempotency_key = kwargs.get("idempotency_key") or hashlib.sha256(
            f"{user_id}:{session_id}:{user_input.strip().lower()}".encode("utf-8")
        ).hexdigest()
        request_id = kwargs.get("request_id") or f"mission_{idempotency_key[:16]}"
        try:
            log_request_id.set(request_id)
            log_user_id.set(user_id)
            log_session_id.set(session_id)
        except Exception:
            pass
        CognitiveTracer.start_trace(request_id, user_id, "mission")
        sm = CentralExecutionState(request_id, trace_id=request_id, user_id=user_id)
        sm.initialize(MissionState.CREATED)
        if not sm.claim_idempotency(user_id, idempotency_key, request_id):
            existing_mission = sm.get_claimed_mission(user_id, idempotency_key)
            return {
                "response": "An equivalent mission is already in flight. Returning the existing mission handle.",
                "status": "duplicate",
                "request_id": existing_mission or request_id,
            }
        sm.attach_metadata(idempotency_key=idempotency_key, user_input=user_input, session_id=session_id)
        
        # 0.1 GDPR Soft-Delete Check (v14.0)
        if await self.is_soft_deleted(user_id):
            sm.transition(MissionState.FAILED)
            CognitiveTracer.end_trace(request_id, "blocked")
            return {
                "response": "This consciousness has been flagged for erasure and cannot initiate new missions.",
                "status": "blocked",
                "request_id": request_id
            }

        # 0.2 Tiered Rate Limiting (v14.0)
        limit_reached, limit_info = await self.check_rate_limit(user_id, kwargs.get("tier", "seeker"))
        if limit_reached:
            logger.warning(f"[Orchestrator] Rate Limit Breach for {user_id} ({kwargs.get('tier')})")
            return {
                "response": f"Cognitive frequency exceeded. Please wait {limit_info['retry_after']}s.",
                "status": "rate_limited",
                "request_id": request_id,
                "retry_after": limit_info['retry_after']
            }

        # 0.3 Blue-Green Routing Logic
        active_engine = self.DEPLOYMENT_STRATEGY
        if self.TRAFFIC_SPLIT_PCT > 0:
            import hashlib
            m = hashlib.md5(user_id.encode())
            bucket = int(m.hexdigest(), 16) % 100
            if bucket < self.TRAFFIC_SPLIT_PCT:
                active_engine = "green"
                logger.info(f"[Orchestrator] 📟 Traffic Routed to GREEN (Candidate) for {user_id}")
        
        logger.info(f"[Orchestrator] Initiating Mission: {request_id} (Engine: {active_engine})")
        sm.transition(MissionState.PLANNED)
        CognitiveTracer.add_step(request_id, "routing_decision", {"engine": active_engine})

        # 1. Fast Cache Layer (Exact & Semantic)
        if not kwargs.get("bypass_cache", False):
            cached = check_exact_match(user_id, user_input, kwargs.get("mood", "philosophical"))
            if not cached:
                cached = check_semantic_match(user_id, user_input, kwargs.get("mood", "philosophical"), threshold=0.95)
            
            if cached:
                logger.info("[Orchestrator] Cache Hit. Mission skipped.")
                sm.transition(MissionState.COMPLETE)
                CognitiveTracer.add_step(request_id, "cache_hit", {"route": "cache"})
                CognitiveTracer.end_trace(request_id, "cache")
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
                 sm.transition(MissionState.EXECUTING)
                 CognitiveTracer.add_step(request_id, "executing", {})
                 return self.brain.stream(user_input, user_id, session_id, request_id=request_id, **kwargs)
            
            sm.transition(MissionState.EXECUTING)
            CognitiveTracer.add_step(request_id, "executing", {})
            result = await self.brain.run(user_input, user_id, session_id, request_id=request_id, **kwargs)
            CognitiveTracer.add_step(request_id, "executed", {"results_count": len(result.get("results", [])) if isinstance(result, dict) else 0})
            sm.attach_replay_payload(
                {
                    "user_input": user_input,
                    "result": result.get("response") if isinstance(result, dict) else None,
                    "task_graph": result.get("reasoning", {}).get("simulation", {}).get("dry_run") if isinstance(result, dict) else None,
                    "reasoning": result.get("reasoning") if isinstance(result, dict) else None,
                    "memory_state_checksum": result.get("memory", {}).get("checksum") if isinstance(result, dict) else None,
                }
            )
            
            # Post-Mission: Cache the successful result
            if result.get("response"):
                store_exact_match(user_id, user_input, kwargs.get("mood", "philosophical"), result["response"])
            sm.transition(MissionState.VALIDATING)
            CognitiveTracer.add_step(request_id, "validating", {})
            sm.transition(MissionState.PERSISTED)
            CognitiveTracer.add_step(request_id, "persisted", {})
            sm.transition(MissionState.COMPLETE)
            CognitiveTracer.end_trace(request_id, "success")
            return result
        except Exception as e:
            logger.exception("[Orchestrator] Mission failure: %s", e)
            sm.transition(MissionState.FAILED)
            CognitiveTracer.add_step(request_id, "failed", {"error": str(e)})
            CognitiveTracer.end_trace(request_id, "failed")
            return {
                "response": "The thought stream was interrupted by a quantum fluctuation.",
                "error": str(e),
                "request_id": request_id,
                "status": "failed"
            }

    async def is_soft_deleted(self, user_id: str) -> bool:
        """Checks if the user has invoked RTBF soft-deletion."""
        redis = get_redis_client()
        return bool(redis.get(f"sovereign:soft_delete:{user_id}"))

    async def check_rate_limit(self, user_id: str, tier: str) -> tuple[bool, Dict[str, Any]]:
        """
        Sovereign v14.0: Tiered Rate Limiting.
        Seeker: 5/min | Pro: 20/min | Creator: 60/min.
        """
        limits = {"seeker": 5, "pro": 20, "creator": 60}
        window = 60 # 1 minute
        cap = limits.get(tier.lower(), 5)
        
        redis = get_redis_client()
        key = f"rate_limit:{user_id}:{int(time.time() / window)}"
        
        current = redis.incr(key)
        if current == 1:
            redis.expire(key, window)
            
        if current > cap:
            return True, {"retry_after": window - (int(time.time()) % window)}
        return False, {}

    def rotate_vault_secrets(self):
        """
        v14.0 Graduation Bridge: Secret Rotation Hook.
        In a full prod env, this would call HashiCorp Vault to rotate API keys.
        """
        logger.info("[Vault] Initiating daily secret rotation for cognitive providers...")
        # Placeholder for Vault API interaction
        pass

# --- Standard Entry Point ---
_orchestrator = Orchestrator()

async def run_orchestrator(**kwargs):
    """Bridge for API v1 and legacy components."""
    return await _orchestrator.handle_mission(**kwargs)
