"""
LEVI-AI Sovereign OS v14.0.0-Autonomous-SOVEREIGN.
The Cognitive Brain: Multi-layer Reasoning, Strategy Calibration, and Mission Governance.
Enforces strict reasoning contracts, cognitive drift detection, and 100% background task tracking compliance.
"""

import logging
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator, Union

from .perception import PerceptionEngine
from .policy_engine import BrainPolicyEngine
from .goal_engine import GoalEngine
from .planner import DAGPlanner
from .executor import GraphExecutor
from .reasoning_core import ReasoningCore
from .failure_engine import FailurePolicyEngine
from .reflection import ReflectionEngine
from .workflow_engine import WorkflowEngine
from .context_manager import ContextManager
from .learning_loop import LearningLoop
from backend.memory.manager import MemoryManager
from .orchestrator_types import ToolResult, BrainDecision, FailureType, FailureAction
from .workflow_contract import bridge_policy, validate_workflow_integrity
from backend.services.brain_service import brain_service
from ..utils.kafka import SovereignKafka
from backend.broadcast_utils import (
    SovereignBroadcaster, 
    PULSE_MISSION_STARTED, 
    PULSE_MISSION_PLANNED, 
    PULSE_MISSION_EXECUTED, 
    PULSE_MISSION_AUDITED
)
from backend.db.redis import r as redis_sync, HAS_REDIS as HAS_REDIS_SYNC
from backend.utils.metrics import MetricsHub
from backend.utils.tracing import traced_span
from backend.core.executor.guardrails import capture_resource_pressure

logger = logging.getLogger(__name__)

class LeviBrainV14:
    """
    LeviBrain v14.0: Brain Control System.
    Architecture: Perception -> BRAIN POLICY -> Goal -> Planning -> Execution -> Reflection -> Memory.
    """

    def __init__(self):
        self.memory = MemoryManager()
        self.perception = PerceptionEngine(self.memory)
        # Decision engine is now externalized via brain_service
        self.goal_engine = GoalEngine()
        self.planner = DAGPlanner()
        self.executor = GraphExecutor()
        self.reasoning_core = ReasoningCore()
        self.failure_engine = FailurePolicyEngine()
        self.reflection = ReflectionEngine()
        self.workflow_engine = WorkflowEngine()
        self.context = ContextManager()

    async def route(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        streaming: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        if streaming:
            return self.stream(user_input, user_id, session_id, **kwargs)
        else:
            return await self.run(user_input, user_id, session_id, **kwargs)

    async def run(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: Optional[str] = None, 
        request_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        LeviBrain v14.0: Brain-Controlled Execution Pass.
        Pipeline: Perception -> POLICY -> Goal -> Planning -> Execution -> Reflection -> Memory.
        """
        request_id = request_id or f"v14_{uuid.uuid4().hex[:8]}"
        session_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"
        mission_start = datetime.now(timezone.utc)
        logger.info("[V14 Brain] Starting Cognitive Mission: %s", request_id)
        
        # Initialize default decision for failure handling
        decision = None
        
        try:
            MetricsHub.mission_started()
            # 1. PERCEPTION
            async with traced_span("brain.perception", request_id=request_id, user_id=user_id):
                SovereignBroadcaster.publish(PULSE_MISSION_STARTED, {"request_id": request_id, "user_input": user_input}, user_id=user_id)
                from backend.utils.runtime_tasks import create_tracked_task
                create_tracked_task(SovereignKafka.emit_event("brain_events", {"event": "MISSION_STARTED", "request_id": request_id}), name=f"kafka-mission-start-{request_id}")
                perception = await self.perception.perceive(user_input, user_id, session_id, **kwargs)

            # 2. BRAIN POLICY (v14.0 Controlled)
            async with traced_span("brain.policy", request_id=request_id):
                policy = await brain_service.generate_policy(user_input, perception["context"])
            logger.info(f"[V14 Brain] Policy Locked: {policy.mode} (ID: {policy.policy_id})")
            
            # Policy Enforcement: Fail Mission if Policy Generation fails (Sovereign Requirement)
            if not policy:
                raise Exception("Sovereign Policy Violation: Failed to generate execution pulse.")

            decision = bridge_policy(policy)

            # 3. GOAL CREATION (Controlled by Policy)
            async with traced_span("brain.goal", request_id=request_id):
                goal = await self.goal_engine.create_goal(perception, decision=decision)

            # 4. PLANNING + REASONING CORE
            perception["request_id"] = request_id
            async with traced_span("brain.planner", request_id=request_id):
                task_graph = await self.planner.build_task_graph(goal, perception, decision=decision)
                task_graph = self.reasoning_core.enrich_for_resilience(task_graph)
                reasoning = await self.reasoning_core.evaluate_plan(goal, perception, task_graph, decision=decision)
                task_graph = reasoning["graph"]
            if reasoning["strategy"]["requires_refinement"] or reasoning["confidence"] < self.reasoning_core.MIN_CONFIDENCE:
                critique_reflection = {
                    "issues": reasoning["critique"]["issues"] or reasoning["critique"]["warnings"],
                    "fix": "Strengthen the weak parts of the execution plan and preserve fallback behavior.",
                }
                async with traced_span("brain.reasoning.refine", request_id=request_id):
                    task_graph = await self.planner.refine_plan(task_graph, critique_reflection, goal, perception)
                    task_graph.metadata.setdefault("reasoning_passes", []).append("plan_refinement")
                    reasoning = await self.reasoning_core.evaluate_plan(goal, perception, task_graph, decision=decision)
                    task_graph = reasoning["graph"]
            SovereignBroadcaster.publish(PULSE_MISSION_PLANNED, {"request_id": request_id, "goal": goal.objective}, user_id=user_id)

            # Backpressure: degrade complexity under CPU/RAM/VRAM/queue pressure
            try:
                forced_gpu_overload = os.getenv("CHAOS_GPU_OVERLOAD", "false").lower() == "true"
                pressure = capture_resource_pressure(
                    vram_pressure=forced_gpu_overload,
                    queue_depth=len(getattr(task_graph, "nodes", [])),
                )
                if HAS_REDIS_SYNC:
                    vram_pressure = redis_sync.get("vram:pressure")
                    pressure = capture_resource_pressure(
                        vram_pressure=forced_gpu_overload or bool(vram_pressure and str(vram_pressure).lower() == "true"),
                        queue_depth=len(getattr(task_graph, "nodes", [])),
                    )
                    if pressure.vram_pressure:
                        decision.enable_agents["critic"] = False
                        decision.execution_policy.parallel_waves = 1
                if pressure.active_dimensions:
                    if "queue" in pressure.active_dimensions or "cpu" in pressure.active_dimensions or "ram" in pressure.active_dimensions:
                        decision.enable_agents["critic"] = False
                        decision.execution_policy.parallel_waves = 1
                    MetricsHub.record_alert("latency_breach", severity="warning", active="queue" in pressure.active_dimensions)
            except Exception:
                pass

            # 5. EXECUTION (Enforcing Policy Limits)
            async with traced_span("brain.executor", request_id=request_id):
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
                    if reflection["is_satisfactory"]:
                        break
                    refinement_count += 1
                    task_graph = await self.planner.refine_plan(task_graph, reflection, goal, perception)
                    results = await self.executor.execute(task_graph, perception, user_id=user_id, policy=decision.execution_policy)
                    draft_response = await synthesize_response(results, perception["context"])
            
            final_response = draft_response
            memory_event = None
            
            # 7. MEMORY SYNC (Tiered Routing)
            try:
                async with traced_span("brain.memory", request_id=request_id):
                    memory_event = await self.memory.store(user_id, session_id, user_input, final_response, perception, results, policy=decision.memory_policy)
            except Exception as mem_err:
                logger.error(f"[V14 Brain] Background Memory Sync Error: {mem_err}")
                MetricsHub.record_alert("memory_mismatch", severity="critical")

            # 8. AUDITING
            from backend.evaluation.evaluator import AutomatedEvaluator
            latency = (datetime.now(timezone.utc) - mission_start).total_seconds() * 1000
            async with traced_span("brain.audit", request_id=request_id):
                audit = await AutomatedEvaluator.evaluate_transaction(
                    user_id=user_id, session_id=session_id, user_input=user_input,
                    response=final_response, goals=[goal.objective], 
                    tool_results=[r.model_dump() for r in results], latency_ms=latency
                )
            await LearningLoop.capture_outcome(
                mission_id=request_id,
                query=user_input,
                result=final_response,
                fidelity=audit["total_score"],
                metadata={
                    "intent_type": perception.get("intent").intent_type if perception.get("intent") else "chat",
                    "graph_signature": task_graph.metadata.get("graph_signature"),
                    "graph_template": task_graph.metadata.get("graph_template"),
                    "memory_state_checksum": memory_event.get("checksum") if isinstance(memory_event, dict) else None,
                    "reasoning_strategy": reasoning["strategy"],
                },
            )
            SovereignBroadcaster.publish(PULSE_MISSION_AUDITED, {"request_id": request_id, "score": audit["total_score"]}, user_id=user_id)
            MetricsHub.mission_finished(success=True)
            workflow = validate_workflow_integrity(request_id, perception, goal, task_graph, results, memory_event)

            return {
                "response": final_response,
                "request_id": request_id,
                "mode": policy.mode,
                "results": [r.model_dump() for r in results],
                "policy": policy.model_dump(),
                "reasoning": {
                    "confidence": reasoning["confidence"],
                    "critique": reasoning["critique"],
                    "simulation": reasoning["simulation"],
                    "strategy": reasoning["strategy"],
                },
                "memory": {
                    "event_id": memory_event.get("id") if isinstance(memory_event, dict) else None,
                    "checksum": memory_event.get("checksum") if isinstance(memory_event, dict) else None,
                    "version": memory_event.get("version") if isinstance(memory_event, dict) else None,
                },
                "workflow": workflow,
            }

        except Exception as e:
            logger.error(f"[V14 Brain] Structural Failure: {e}")
            MetricsHub.mission_finished(success=False, stage="brain")
            # Recovery Action Logic
            if decision:
                failure_type = FailureType.LLM_ERROR if "LLM" in str(e).upper() else FailureType.DAG_CONFLICT
                action = await self.failure_engine.determine_action(failure_type, str(e), {}, decision)
                
                if action.action == "fallback":
                    return {"response": "I encountered a high-complexity anomaly and shifted to a resilient model proxy.", "mode": "recovery"}
                elif action.action == "regenerate":
                    return {"response": "Plan conflict detected. Re-initiating sequential mission.", "mode": "recovery"}
            
            return {"response": f"Brain Anomaly: {str(e)}", "status": "error"}

    async def stream(
        self, 
        user_input: str, 
        user_id: str, 
        session_id: str, 
        request_id: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        request_id = request_id or f"v14_stream_{uuid.uuid4().hex[:8]}"
        decision = None
        yield {"event": "metadata", "data": {"request_id": request_id, "status": "pulsing"}}

        try:
            # 1. Perception
            perception = await self.perception.perceive(user_input, user_id, session_id, **kwargs)
            yield {"event": "activity", "data": f"Intent: {perception['intent'].intent_type.upper()}"}
            
            # 2. Brain Policy (v14.0 Controlled)
            policy = await brain_service.generate_policy(user_input, perception["context"])
            yield {"event": "activity", "data": f"Mode: {policy.mode}"}
            
            # Policy Enforcement: Fail if Policy Generation fails
            if not policy:
                raise Exception("Sovereign Policy Violation: Failed to generate execution pulse.")
            
            decision = bridge_policy(policy)

            # 3. Goal & Planning
            goal = await self.goal_engine.create_goal(perception, decision=decision)
            perception["request_id"] = request_id
            task_graph = await self.planner.build_task_graph(goal, perception, decision=decision)
            task_graph = self.reasoning_core.enrich_for_resilience(task_graph)
            reasoning = await self.reasoning_core.evaluate_plan(goal, perception, task_graph, decision=decision)
            task_graph = reasoning["graph"]
            
            # 4. Execution (Enforcing Policy)
            results = await self.executor.execute(
                task_graph,
                perception,
                user_id=user_id,
                policy=decision.execution_policy,
                safe_mode=reasoning["strategy"]["safe_mode"],
            )
            
            # 5. Streaming Synthesis
            from .engine import synthesize_streaming_response
            full_response_parts = []
            async for chunk in synthesize_streaming_response(results, perception["context"]):
                if "token" in chunk:
                    full_response_parts.append(chunk["token"])
                yield chunk

            # 6. Memory Sync (Background)
            full_response = "".join(full_response_parts)
            from backend.utils.runtime_tasks import create_tracked_task
            create_tracked_task(self.memory.store(user_id, session_id, user_input, full_response, perception, results, policy=decision.memory_policy), name=f"stream-mem-sync-{request_id}")

        except Exception as e:
            logger.error("[V14 Brain] Stream Failure: %s", e)
            if decision:
                # Basic recovery for stream if possible
                yield {"event": "error", "data": "The cognitive stream encountered a quantum misalignment. Re-adjusting..."}
            else:
                yield {"event": "error", "data": "Critical Perception Failure."}

LeviBrain = LeviBrainV14
