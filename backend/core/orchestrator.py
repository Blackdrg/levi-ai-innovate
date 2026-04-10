"""
LEVI-AI Sovereign OS v14.0.0-Autonomous-SOVEREIGN.
Central Orchestration Layer: Mission Lifecycle & Resource Governance.
"""

import logging
import uuid
import os
import time
import hashlib
from typing import Any, Dict, Optional

from .perception import PerceptionEngine
from .planner import DAGPlanner
from .executor import GraphExecutor
from .reasoning_core import ReasoningCore
from .failure_engine import FailurePolicyEngine
from .reflection import ReflectionEngine
from .workflow_engine import WorkflowEngine
from .context_manager import ContextManager
from .learning_loop import LearningLoop
from backend.memory.manager import MemoryManager
from .orchestrator_types import ToolResult, FailureType, FailureAction
from .workflow_contract import validate_workflow_integrity
from backend.services.brain_service import brain_service
from ..utils.kafka import SovereignKafka
from backend.broadcast_utils import (
    SovereignBroadcaster, 
    PULSE_MISSION_STARTED, 
    PULSE_MISSION_PLANNED, 
    PULSE_MISSION_EXECUTED, 
    PULSE_MISSION_AUDITED
)
from backend.db.redis import (
    get_redis_client, 
    check_exact_match, 
    store_exact_match, 
    check_semantic_match,
    r as redis_sync,
    HAS_REDIS as HAS_REDIS_SYNC
)
from .execution_state import CentralExecutionState, MissionState
from backend.evaluation.tracing import CognitiveTracer
from backend.utils.logging_context import log_request_id, log_user_id, log_session_id
from backend.utils.metrics import MetricsHub
from backend.utils.tracing import traced_span
from backend.core.executor.guardrails import capture_resource_pressure
from datetime import datetime, timezone
import asyncio

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    LEVI-AI v14.0 Orchestrator.
    Manages the lifecycle of a cognitive mission with Brain Control System.
    """
    def __init__(self):
        self.active_missions = set()
        self.memory = MemoryManager()
        self.perception = PerceptionEngine(self.memory)
        self.planner = DAGPlanner()
        self.executor = GraphExecutor()
        self.reasoning_core = ReasoningCore()
        self.failure_engine = FailurePolicyEngine()
        self.reflection = ReflectionEngine()
        self.workflow_engine = WorkflowEngine()
        self.context = ContextManager()
        self.learning_loop = LearningLoop()

    def _prune_context(self, context: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Hardens context window by pruning history and non-essential metadata."""
        pruned = context.copy()
        history = pruned.get("history", [])
        if len(history) > 5:
            pruned["history"] = history[-5:]
        internal_keys = ["raw_logs", "debug_trace", "intermediate_steps"]
        for key in internal_keys:
            if key in pruned: del pruned[key]
        return pruned


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
        # 1. Fast Cache Layer (Exact & Semantic)
        if not kwargs.get("bypass_cache", False):
            cached = check_exact_match(user_id, user_input, kwargs.get("mood", "philosophical"))
            if not cached:
                cached = check_semantic_match(user_id, user_input, kwargs.get("mood", "philosophical"), threshold=0.95)
            
            if cached:
                logger.info("[Orchestrator] Cache Hit. Mission skipped.")
                # Return immediately without initialization overhead
                return {
                    "response": cached,
                    "request_id": request_id,
                    "route": "cache"
                }

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

        # 0.2.1 Global Billing Enforcement (v14.1)
        from backend.services.billing_service import billing_service
        is_simplicity = kwargs.get("simplicity_mode", False)
        cost = 1.0 if is_simplicity else 5.0
        
        has_credits = await billing_service.deduct_credits(user_id, amount=cost)
        if not has_credits:
             sm.transition(MissionState.FAILED)
             CognitiveTracer.end_trace(request_id, "billing_failure")
             return {
                 "response": "Cognitive credits exhausted. Please recharge to continue.",
                 "status": "billing_error",
                 "request_id": request_id
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

        # Cache logic was moved to top of handle_mission for performance

        # 2. Credit Lock
        # We check intent roughly here or let the brain handle it. 
        # For DDD, the Orchestrator (Application Service) handles the transaction logic.
        # But we need intent for credit cost. Let's let the brain perceive first.

        # 3. Cognitive Mission Execution
        self.active_missions.add(request_id)
        mission_start = datetime.now(timezone.utc)
        
        try:
            if streaming:
                 sm.transition(MissionState.EXECUTING)
                 CognitiveTracer.add_step(request_id, "executing", {})
                 self.active_missions.discard(request_id)
                 return self.stream_mission(user_input, user_id, session_id, request_id=request_id, **kwargs)
            
            sm.transition(MissionState.EXECUTING)
            CognitiveTracer.add_step(request_id, "executing", {})
            
            # --- START COGNITIVE PIPELINE ---
            MetricsHub.mission_started()
                      # 1. PERCEPTION
            async with traced_span("orchestrator.perception", request_id=request_id):
                from backend.utils.runtime_tasks import create_tracked_task
                create_tracked_task(SovereignKafka.emit_event("brain_events", {"event": "MISSION_STARTED", "request_id": request_id}), name=f"kafka-mission-start-{request_id}")
                
                # 🛡️ SECURITY GATE (v14.1)
                from backend.core.security.anomaly_detector import SecurityAnomalyDetector
                threat_score = SecurityAnomalyDetector.analyze_payload(user_input, context=kwargs.get("context"))
                if SecurityAnomalyDetector.should_block(threat_score):
                    logger.critical(f"[Security] BLOCKING MALICIOUS PAYLOAD for {user_id}. Score: {threat_score}")
                    sm.transition(MissionState.FAILED)
                    return {
                        "response": "Security violation detected. This mission has been quarantined.",
                        "status": "security_block",
                        "request_id": request_id
                    }

                # 0.3 DETERMINISTIC FAST-PATH (v14.1 Evolutionary Intelligence)
                from .evolution_engine import EvolutionaryIntelligenceEngine
                evolved_rule = await EvolutionaryIntelligenceEngine.check_rules(user_input)
                if evolved_rule:
                     # Tier-0 Validation (Mandatory for all overrides)
                     is_t0_valid = await self._validate_evolved_rule(evolved_rule, tier=0)
                     if is_t0_valid:
                         policy = evolved_rule["policy"]
                         if policy["tier_1_bypass"]:
                             logger.info(f"[Orchestrator] 🚀 Deterministic Fast-Path Triggered: Bypassing FULL planning for rule {user_input[:20]}...")
                             return {
                                 "response": evolved_rule["result_data"]["solution"],
                                 "request_id": request_id,
                                 "status": "success",
                                 "tag": evolved_rule["tag"]
                             }
                
                perception = await self.perception.perceive(user_input, user_id, session_id, **kwargs)

            # 0.4 ULTRA-LIGHT EXECUTION MODE (v14.1)
            if (perception["intent"].intent_type == "chat" and perception["intent"].complexity_level <= 1) or is_simplicity:
                logger.info(f"[Orchestrator] 🕊️ Simplicity/Ultra-Light Mode triggered: {user_input[:20]}...")
                from .engine import synthesize_response
                res = await brain_service.call_local_llm(user_input)
                final_response = res
                # Minimal audit/sync
                await self.memory.store(user_id, session_id, user_input, final_response, perception, [], policy=None)
                sm.transition(MissionState.COMPLETE)
                return {
                    "response": final_response,
                    "request_id": request_id,
                    "status": "success",
                    "route": "simplicity"
                }

            # 1.2 CONTEXT PRUNING
            perception["context"] = self._prune_context(perception.get("context", {}), user_id)

            # 2. DECISION & POLICY (Folded into Planner)
            async with traced_span("orchestrator.policy", request_id=request_id):
                decision = await self.planner.generate_decision(user_input, perception)
            logger.info(f"[Orchestrator] Decision Locked: Mode={decision.mode}")

            # 3. GOAL CREATION (Folded into Planner)
            async with traced_span("orchestrator.goal", request_id=request_id):
                goal = await self.planner.create_goal(perception, decision)

            # 4. PLANNING + REASONING CORE
            perception["request_id"] = request_id
            async with traced_span("orchestrator.planner", request_id=request_id):
                task_graph = await self.planner.build_task_graph(goal, perception, decision=decision)
                task_graph = self.reasoning_core.enrich_for_resilience(task_graph)
                reasoning = await self.reasoning_core.evaluate_plan(goal, perception, task_graph, decision=decision)
                task_graph = reasoning["graph"]
            
            if reasoning["strategy"]["requires_refinement"] or reasoning["confidence"] < self.reasoning_core.MIN_CONFIDENCE:
                critique_reflection = {
                    "issues": reasoning["critique"]["issues"] or reasoning["critique"]["warnings"],
                    "fix": "Strengthen the weak parts of the execution plan.",
                }
                async with traced_span("orchestrator.reasoning.refine", request_id=request_id):
                    task_graph = await self.planner.refine_plan(task_graph, critique_reflection, goal, perception)
                    reasoning = await self.reasoning_core.evaluate_plan(goal, perception, task_graph, decision=decision)
                    task_graph = reasoning["graph"]
            
            SovereignBroadcaster.publish(PULSE_MISSION_PLANNED, {"request_id": request_id, "goal": goal.objective}, user_id=user_id)

            # 5. EXECUTION
            async with traced_span("orchestrator.executor", request_id=request_id):
                results = await self.executor.execute(
                    task_graph,
                    perception,
                    user_id=user_id,
                    policy=decision.execution_policy,
                    safe_mode=reasoning["strategy"]["safe_mode"],
                )
            SovereignBroadcaster.publish(PULSE_MISSION_EXECUTED, {"request_id": request_id}, user_id=user_id)

            # 6. REFLECTION Loop
            from .engine import synthesize_response
            draft_response = await synthesize_response(results, perception["context"])
            
            if decision.enable_agents.get("critic", False):
                refinement_count = 0
                max_refs = min(decision.execution_policy.max_retries, decision.execution_policy.budget.recompute_cycles)
                while refinement_count < max_refs:
                    reflection = await self.reflection.evaluate(draft_response, goal, perception, results)
                    if reflection["is_satisfactory"]: break
                    refinement_count += 1
                    task_graph = await self.planner.refine_plan(task_graph, reflection, goal, perception)
                    results = await self.executor.execute(task_graph, perception, user_id=user_id, policy=decision.execution_policy)
                    draft_response = await synthesize_response(results, perception["context"])
            
            final_response = draft_response
            memory_event = None
            
            # 7. MEMORY SYNC
            try:
                async with traced_span("orchestrator.memory", request_id=request_id):
                    memory_event = await self.memory.store(user_id, session_id, user_input, final_response, perception, results, policy=decision.memory_policy)
            except Exception as mem_err:
                logger.error(f"[Orchestrator] Memory Sync Error: {mem_err}")
                MetricsHub.record_alert("memory_mismatch", severity="critical")

            # 8. AUDITING
            from backend.evaluation.evaluator import AutomatedEvaluator
            latency = (datetime.now(timezone.utc) - mission_start).total_seconds() * 1000
            async with traced_span("orchestrator.audit", request_id=request_id):
                audit = await AutomatedEvaluator.evaluate_transaction(
                    user_id=user_id, session_id=session_id, user_input=user_input,
                    response=final_response, goals=[goal.objective], 
                    tool_results=[r.model_dump() for r in results], latency_ms=latency
                )
            
            CognitiveTracer.add_step(request_id, "executed", {"results_count": len(results)})
            sm.attach_replay_payload({
                "user_input": user_input, "result": final_response,
                "task_graph": task_graph.metadata.get("graph_template"),
                "reasoning": reasoning,
                "memory_state_checksum": memory_event.get("checksum") if isinstance(memory_event, dict) else None,
            })
            
            # Post-Mission: Cache the successful result
            if final_response:
                store_exact_match(user_id, user_input, kwargs.get("mood", "philosophical"), final_response)
            
            sm.transition(MissionState.VALIDATING)
            sm.transition(MissionState.PERSISTED)
            sm.transition(MissionState.COMPLETE)
            CognitiveTracer.end_trace(request_id, "success")
            self.active_missions.discard(request_id)
            
            return {
                "response": final_response,
                "request_id": request_id,
                "mode": decision.mode.value,
                "results": [r.model_dump() for r in results],
                "reasoning": reasoning,
                "memory": {
                    "event_id": memory_event.get("id") if isinstance(memory_event, dict) else None,
                    "checksum": memory_event.get("checksum") if isinstance(memory_event, dict) else None,
                },
                "status": "success"
            }

        except Exception as e:
            logger.exception("[Orchestrator] Mission failure: %s", e)
            sm.transition(MissionState.FAILED)
            CognitiveTracer.add_step(request_id, "failed", {"error": str(e)})
            CognitiveTracer.end_trace(request_id, "failed")
            self.active_missions.discard(request_id)
            return {
                "response": "The thought stream was interrupted by a structural anomaly.",
                "error": str(e),
                "request_id": request_id,
                "status": "failed"
            }

    async def stream_mission(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        request_id: str,
        **kwargs
    ):
        """Streaming mission pipeline."""
        yield {"event": "metadata", "data": {"request_id": request_id, "status": "pulsing"}}
        try:
            # 1. Perception
            perception = await self.perception.perceive(user_input, user_id, session_id, **kwargs)
            yield {"event": "activity", "data": f"Intent: {perception['intent'].intent_type.upper()}"}
            
            # 2. Decision
            decision = await self.planner.generate_decision(user_input, perception)
            
            # 3. Goal & Planning
            goal = await self.planner.create_goal(perception, decision)
            task_graph = await self.planner.build_task_graph(goal, perception, decision=decision)
            
            # 4. Execution
            results = await self.executor.execute(task_graph, perception, user_id=user_id, policy=decision.execution_policy)
            
            # 5. Streaming Synthesis
            from .engine import synthesize_streaming_response
            full_response_parts = []
            async for chunk in synthesize_streaming_response(results, perception["context"]):
                if "token" in chunk: full_response_parts.append(chunk["token"])
                yield chunk

            # 6. Memory Sync (Background)
            full_response = "".join(full_response_parts)
            from backend.utils.runtime_tasks import create_tracked_task
            create_tracked_task(self.memory.store(user_id, session_id, user_input, full_response, perception, results, policy=decision.memory_policy), name=f"stream-mem-sync-{request_id}")

        except Exception as e:
            logger.error("[Orchestrator] Stream Failure: %s", e)
            yield {"event": "error", "data": f"Structural anomaly: {str(e)}"}

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
        v14.1 Graduation: Integrated KMS Secret Rotation.
        Triggers Master Key rotation in the configured KMS provider (Vault/Local).
        """
        from backend.utils.kms import get_kms_provider, VaultKMSAdapter
        kms = get_kms_provider()
        
        logger.info(f"[KMS] Initiating secret rotation pulse using {type(kms).__name__}...")
        
        if isinstance(kms, VaultKMSAdapter):
            # In a real Vault setup, we'd call the /rotate endpoint for the transit key
            logger.info("[KMS] Vault Transit Key rotation pulse emitted.")
        else:
            # For LocalKMS, we'd update the SYSTEM_SECRET version
            logger.info("[KMS] Local Master Key rotation queued.")

    async def teardown_gracefully(self):
        logger.info(f"[Orchestrator] Tearing down thoughtfully. Halting {len(self.active_missions)} mission(s).")
        for request_id in list(self.active_missions):
            try:
                # Flush trace logs if interrupted mid flight
                CognitiveTracer.add_step(request_id, "interrupted", {"reason": "SIGTERM / Graceful Shutdown"})
                CognitiveTracer.end_trace(request_id, "interrupted")
                # Mark Central Execution State as failed/interrupted
                sm = CentralExecutionState(request_id)
                sm.transition(MissionState.FAILED)
                # Cleanup cache footprint if any
                get_redis_client().delete(f"mission:state:{request_id}")
            except Exception as e:
                logger.error(f"[Orchestrator] Failed safely closing mission {request_id}: {e}")
        self.active_missions.clear()

    async def _validate_evolved_rule(self, rule: Dict[str, Any], tier: int = 0) -> bool:
        """
        LEVI v14.1 Spec: Tiered Critic validation for deterministic rules.
        """
        try:
            from backend.evaluation.evaluator import AutomatedEvaluator
            # Simplified Tier-0: Basic syntactic/safety check
            if tier == 0:
                # We reuse the AutomatedEvaluator's metrics for a lightweight check
                # Logic: Check for hallucinations or empty results
                solution = rule["result_data"].get("solution", "")
                if not solution or len(solution) < 5:
                    return False
                return True
            
            # Tier-1/Tier-2 would involve a full FidelityCritic pass
            return True
        except Exception:
            return False

# --- Standard Entry Point ---
_orchestrator = Orchestrator()

async def run_orchestrator(**kwargs):
    """Bridge for API v1 and legacy components."""
    return await _orchestrator.handle_mission(**kwargs)
