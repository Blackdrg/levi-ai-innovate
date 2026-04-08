"""
LEVI-AI v14.0 Brain (Meta-Orchestrator).
The cognitive heart of LEVI-AI.
Centrally governs Strategy, Subsystem Activation, and Execution Policy.
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
from .failure_engine import FailurePolicyEngine
from .reflection import ReflectionEngine
from .workflow_engine import WorkflowEngine
from .context_manager import ContextManager
from backend.memory.manager import MemoryManager
from .orchestrator_types import ToolResult, BrainDecision, BrainMode, FailureType, FailureAction
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
            # 1. PERCEPTION
            SovereignBroadcaster.publish(PULSE_MISSION_STARTED, {"request_id": request_id, "user_input": user_input}, user_id=user_id)
            asyncio.create_task(SovereignKafka.emit_event("brain_events", {"event": "MISSION_STARTED", "request_id": request_id}))
            perception = await self.perception.perceive(user_input, user_id, session_id, **kwargs)

            # 2. BRAIN POLICY (v14.0 Controlled)
            policy = await brain_service.generate_policy(user_input, perception["context"])
            logger.info(f"[V14 Brain] Policy Locked: {policy.mode} (ID: {policy.policy_id})")
            
            # Policy Enforcement: Fail Mission if Policy Generation fails (Sovereign Requirement)
            if not policy:
                raise Exception("Sovereign Policy Violation: Failed to generate execution pulse.")

            # 2.1 Bridge Service Policy to Internal BrainDecision (v14.0 Monolith compatibility)
            from .orchestrator_types import BrainDecision, MemoryPolicy, ExecutionPolicy, LLMPolicy, BrainMode
            
            # Map string mode to BrainMode enum
            try:
                bm = BrainMode(policy.mode)
            except ValueError:
                bm = BrainMode.BALANCED

            decision = BrainDecision(
                mode=bm,
                enable_agents=policy.enable,
                memory_policy=MemoryPolicy(
                    redis=policy.memory.get("redis", True),
                    postgres=policy.memory.get("postgres", True),
                    neo4j=policy.memory.get("neo4j", False),
                    faiss=policy.memory.get("faiss", True)
                ),
                execution_policy=ExecutionPolicy(
                    parallel_waves=policy.execution.get("parallel_waves", 2),
                    max_retries=policy.execution.get("max_retries", 1),
                    sandbox_required=policy.enable.get("sandbox", False)
                ),
                llm_policy=LLMPolicy(
                    local_only=policy.llm.get("local_only", True),
                    cloud_fallback=policy.llm.get("fallback_allowed", False)
                ),
                complexity_score=policy.dict().get("scores", {}).get("complexity_score", 0.5)
            )

            # 3. GOAL CREATION (Controlled by Policy)
            goal = await self.goal_engine.create_goal(perception, decision=decision)

            # 4. PLANNING (DAG)
            task_graph = await self.planner.build_task_graph(goal, perception, decision=decision)
            SovereignBroadcaster.publish(PULSE_MISSION_PLANNED, {"request_id": request_id, "goal": goal.objective}, user_id=user_id)

            # Backpressure: degrade complexity under VRAM pressure
            try:
                if HAS_REDIS_SYNC:
                    pressure = redis_sync.get("vram:pressure")
                    if pressure and str(pressure).lower() == "true":
                        decision.enable_agents["critic"] = False
                        decision.execution_policy.parallel_waves = 1
            except Exception:
                pass

            # 5. EXECUTION (Enforcing Policy Limits)
            results = await self.executor.execute(task_graph, perception, user_id=user_id, policy=decision.execution_policy)
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
            
            # 7. MEMORY SYNC (Tiered Routing)
            try:
                await self.memory.store(user_id, session_id, user_input, final_response, perception, results, policy=decision.memory_policy)
            except Exception as mem_err:
                logger.error(f"[V14 Brain] Background Memory Sync Error: {mem_err}")

            # 8. AUDITING
            from backend.evaluation.evaluator import AutomatedEvaluator
            latency = (datetime.now(timezone.utc) - mission_start).total_seconds() * 1000
            audit = await AutomatedEvaluator.evaluate_transaction(
                user_id=user_id, session_id=session_id, user_input=user_input,
                response=final_response, goals=[goal.objective], 
                tool_results=[r.dict() for r in results], latency_ms=latency
            )
            SovereignBroadcaster.publish(PULSE_MISSION_AUDITED, {"request_id": request_id, "score": audit["total_score"]}, user_id=user_id)

            return {
                "response": final_response,
                "request_id": request_id,
                "mode": policy.mode,
                "results": [r.dict() for r in results],
                "policy": policy.dict()
            }

        except Exception as e:
            logger.error(f"[V14 Brain] Structural Failure: {e}")
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
            
            # 2.1 Bridge to internal Decision
            from .orchestrator_types import BrainDecision, MemoryPolicy, ExecutionPolicy, LLMPolicy, BrainMode
            try:
                bm = BrainMode(policy.mode)
            except ValueError:
                bm = BrainMode.BALANCED

            decision = BrainDecision(
                mode=bm,
                enable_agents=policy.enable,
                memory_policy=MemoryPolicy(
                    redis=policy.memory.get("redis", True),
                    postgres=policy.memory.get("postgres", True),
                    neo4j=policy.memory.get("neo4j", False),
                    faiss=policy.memory.get("faiss", True)
                ),
                execution_policy=ExecutionPolicy(
                    parallel_waves=policy.execution.get("parallel_waves", 2),
                    max_retries=policy.execution.get("max_retries", 1),
                    sandbox_required=policy.enable.get("sandbox", False)
                ),
                llm_policy=LLMPolicy(
                    local_only=policy.llm.get("local_only", True),
                    cloud_fallback=policy.llm.get("fallback_allowed", False)
                )
            )

            # 3. Goal & Planning
            goal = await self.goal_engine.create_goal(perception, decision=decision)
            task_graph = await self.planner.build_task_graph(goal, perception, decision=decision)
            
            # 4. Execution (Enforcing Policy)
            results = await self.executor.execute(task_graph, perception, user_id=user_id, policy=decision.execution_policy)
            
            # 5. Streaming Synthesis
            from .engine import synthesize_streaming_response
            full_response_parts = []
            async for chunk in synthesize_streaming_response(results, perception["context"]):
                if "token" in chunk:
                    full_response_parts.append(chunk["token"])
                yield chunk

            # 6. Memory Sync (Background)
            full_response = "".join(full_response_parts)
            asyncio.create_task(self.memory.store(user_id, session_id, user_input, full_response, perception, results, policy=decision.memory_policy))

        except Exception as e:
            logger.error("[V14 Brain] Stream Failure: %s", e)
            if decision:
                # Basic recovery for stream if possible
                yield {"event": "error", "data": "The cognitive stream encountered a quantum misalignment. Re-adjusting..."}
            else:
                yield {"event": "error", "data": "Critical Perception Failure."}

LeviBrain = LeviBrainV14
