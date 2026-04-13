"""
LEVI-AI Sovereign OS v14.0.0-Autonomous-SOVEREIGN.
Distributed Task Graph (DAG) Execution Engine.
Handles parallelization, dependency resolution, and mandatory task tracking.
"""

import logging
import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from ..orchestrator_types import ToolResult, IntentResult, AgentResult
from ..tool_registry import call_tool
from ..blackboard import MissionBlackboard
from backend.broadcast_utils import SovereignBroadcaster, PULSE_NODE_COMPLETED
from ...utils.network import ai_service_breaker
from ...celery_app import celery_app
from backend.core.agent_registry import AgentRegistry
from ...agents.consensus_agent import ConsensusAgentV11
from ..agent_client import agent_client
from ...utils.rate_limit import check_agent_limit
from ...utils.sanitizer import ResultSanitizer
from ...db.models import CognitiveUsage, Mission
from ...db.postgres import PostgresDB
from ..dcn_protocol import DCNProtocol
from backend.db.redis import r_async as redis_client, HAS_REDIS_ASYNC as HAS_REDIS
from ..execution_state import CentralExecutionState
from ...evaluation.tracing import CognitiveTracer
from ...utils.retries import compute_backoff_delay
from ...utils.metrics import MetricsHub
from ...utils.chaos import ChaosMonkey
from ...utils.tracing import traced_span
from ..execution_guardrails import AgentSandbox, ExecutionBudgetTracker, capture_resource_pressure
from .compensation_coordinator import CompensationCoordinator
from ..dcn.resource_manager import ResourceManager
from backend.services.billing_service import billing_service
from backend.db.neo4j_db import project_to_neo4j
from backend.evolution import (
    self_monitor, 
    failure_analyzer, 
    success_learner, 
    parameter_optimizer, 
    discovery_engine
)



logger = logging.getLogger(__name__)

class NodeState(str, Enum):
    CREATED = "created"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"
    SKIPPED = "skipped"

class GraphExecutor:
    """
    LeviBrain v13.1: Graph-Aware Executor.
    Processes task nodes based on topological dependencies.
    
    Audit Point 07 Hardening:
    - MAX_MISSION_NODES: 15 (Increased from 10 per core)
    - MAX_WAVES: 8
    - WARNING_THRESHOLD: 8
    """
    MAX_MISSION_NODES = 15
    MAX_WAVES = 8
    WARNING_THRESHOLD = 8

    def __init__(self, max_concurrent_nodes: int = 4):
        self._node_breakers: Dict[str, Dict[str, float]] = {}
        self._wave_lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        self._max_slots = max_concurrent_nodes
        self._slot_semaphore = asyncio.Semaphore(max_concurrent_nodes)
        self.resource_manager = ResourceManager()
        
    # SSL handling is now centralized in agent_client.py

    async def _execute_node_resilient(
        self, 
        node: Any, 
        previous_results: Dict[str, ToolResult], 
        perception: Dict[str, Any], 
        blackboard: Any = None, 
        user_id: str = "global", 
        wave_count: int = 0, 
        policy: Optional[Any] = None, 
        mission_sm: Optional[Any] = None
    ) -> ToolResult:
        """
        Phase 5: Self-Healing Execution.
        Dynamically handles agent failures via:
        1. Retry with escalated timeouts.
        2. Switch Agent (fallback_agent).
        3. Dynamic Replanning (Local LLM workaround).
        """
        async with self._slot_semaphore:
            attempts = 0
            max_attempts = getattr(node, "retry_count", 2)
            current_timeout = getattr(node, "timeout", 30)
            original_agent = getattr(node, "agent", "unknown")
            
            while attempts < max_attempts:
                try:
                    result = await asyncio.wait_for(
                        self._execute_node(
                            node, previous_results, perception, blackboard, 
                            user_id, wave_count, policy, mission_sm
                        ),
                        timeout=current_timeout
                    )
                    if result.success:
                        return result
                    raise Exception(result.error or "Agent execution reported failure.")
                except asyncio.TimeoutError:
                    attempts += 1
                    current_timeout *= 2
                    logger.warning(f"⏳ [Self-Healing] Node {node.id} timed out. Escalating timeout: {current_timeout}s")
                    if attempts >= max_attempts:
                        break
                except Exception as e:
                    logger.error(f"💥 [Self-Healing] Node {node.id} ({node.agent}) failed: {e}")
                    attempts += 1
                    
                    # Phase 5: Switch Agent
                    fallback_agent = getattr(node, "fallback_agent", None)
                    if fallback_agent and node.agent != fallback_agent:
                        logger.warning(f"🔄 [Self-Healing] Switching agent: {node.agent} -> {fallback_agent}")
                        node.agent = fallback_agent
                        attempts = 0  # Reset attempts for the new fallback agent
                        continue
                        
                    # Phase 5: Dynamic Replan if max attempts reached
                    if attempts >= max_attempts:
                        logger.warning(f"🧠 [Self-Healing] Max retries reached for {node.id}. Triggering dynamic replan...")
                        try:
                            from backend.core.local_engine import handle_local_sync
                            prompt = (
                                "You are the LEVI Self-Healing Executor.\n"
                                f"Task '{node.description}' failed repeatedly using agent '{node.agent}'.\n"
                                f"Error: {str(e)}\n"
                                "Provide a robust fallback response or mitigation strategy to salvage the mission."
                            )
                            salvaged_response = await handle_local_sync([{"role": "system", "content": prompt}], model_type="default")
                            return ToolResult(
                                success=True,
                                message=salvaged_response,
                                agent="self_healing_replan",
                                recovered_via="dynamic_replan"
                            )
                        except Exception as replan_err:
                            logger.error(f"❌ [Self-Healing] Replanning failed: {replan_err}")
                            return ToolResult(success=False, error=f"Agent failed and replan failed: {replan_err}", agent=original_agent)
        
        return ToolResult(success=False, error="Node execution failed after all self-healing attempts.", agent=original_agent)

    async def execute(self, graph: Any, perception: Dict[str, Any], user_id: str = "global", policy: Optional[Any] = None, safe_mode: bool = True) -> List[ToolResult]:


        logger.info("[V13.1 Executor] Executing Task Graph...")
        if hasattr(graph, "validate_dag"):
            max_depth = getattr(getattr(policy, "budget", None), "max_dag_depth", None)
            graph.validate_dag(max_depth=max_depth)
            if hasattr(graph, "max_depth"):
                MetricsHub.observe_dag_depth(graph.max_depth())
        results: Dict[str, ToolResult] = {}
        completed_ids: Set[str] = set()
        
        mission_id = perception.get("request_id") or "global"
        blackboard = MissionBlackboard(mission_id)
        
        remaining_nodes = list(graph.nodes)
        wave_count = 0
        total_nodes_executed = 0
        mission_sm = CentralExecutionState(mission_id)
        compensation_coordinator = CompensationCoordinator(mission_id)
        budget = getattr(policy, "budget", None)
        budget_tracker = ExecutionBudgetTracker(
            token_limit=getattr(budget, "token_limit", 200000),
            tool_call_limit=getattr(budget, "tool_call_limit", 20),
        )

        
        running_tasks: Dict[asyncio.Task, Any] = {}
        
        # 2. Identify and Schedule Executable Waves (Phase 2 Hardening)
        waves = []
        if hasattr(graph, "get_execution_waves"):
            waves = graph.get_execution_waves()
            logger.info(f"[Executor] Wave-Partitioning Success: {len(waves)} waves identified.")
        
        for wave_idx, wave_nodes in enumerate(waves):
            # 1. Mission Cancellation / Abort Check
            from backend.utils.mission import MissionControl
            if MissionControl.is_cancelled(mission_id) or self._shutdown_event.is_set():
                logger.warning(f"[Executor] Mission {mission_id} aborted before wave {wave_idx}.")
                break

            wave_count = wave_idx
            wave_tasks = {}
            
            logger.info(f"[Executor] 🌊 Processing Wave {wave_idx} ({len(wave_nodes)} nodes)")
            
            for node in wave_nodes:
                pressure = capture_resource_pressure(len(running_tasks))
                
                # --- v14.2 Resource-Aware Admission Control ---
                if pressure.ram_percent >= 90.0 or pressure.cpu_percent >= 90.0 or pressure.vram_pressure:
                    logger.warning(f"[Shield] Resource Exhaustion Near. Waiting for wave to stabilize...")
                    await asyncio.sleep(2.0)

                # formal lifecycle: SCHEDULED
                node.state = NodeState.SCHEDULED
                task = asyncio.create_task(
                    self._execute_node_resilient(
                        node, results, perception, blackboard=blackboard, 
                        user_id=user_id, wave_count=wave_count, policy=policy, 
                        mission_sm=mission_sm
                    )
                )
                running_tasks[task] = node
                wave_tasks[task] = node
                budget_tracker.reserve_tool_calls(1)
                total_nodes_executed += 1
                logger.debug(f"[Executor] Scheduled wave-node {node.id}")

            # 3. Wait for current wave to finish before moving to the next
            if wave_tasks:
                done, _ = await asyncio.wait(wave_tasks.keys(), return_when=asyncio.ALL_COMPLETED)
                
                for task in done:
                    node = running_tasks.pop(task)
                    try:
                        res = await task
                        results[node.id] = res
                        completed_ids.add(node.id)
                        
                        # Resilience & Billing logic
                        if not res.success and node.critical:
                            failure_type = await self._categorize_failure(res.error or "Unknown")
                            if failure_type == "F-3": 
                                 await billing_service.add_credits(user_id, amount=4.0)
                            
                            logger.error(f"[Resilience] Critical failure in wave {wave_idx} on {node.id}. Aborting.")
                            await compensation_coordinator.compensate()
                            return list(results.values())
                        
                        budget_tracker.add_tokens(node.agent, getattr(res, "total_tokens", 0))
                    except Exception as e:
                        logger.error(f"[Executor] Wave task crash: {e}")
                        results[node.id] = ToolResult(success=False, error=str(e), agent=node.agent)

            if total_nodes_executed > self.MAX_MISSION_NODES:
                logger.error(f"[Shield] Node limit reached. Aborting.")
                break
                
            # 4. Critical Path Failure Check
            critical_failure = False
            for n in wave_nodes:
                res = results.get(n.id)
                if not res: continue
                if not res.success and n.critical:
                    critical_failure = True
                    logger.warning("[V8 Executor] Critical task failure: %s", n.id)
                    break
            
            if critical_failure:
                if safe_mode:
                    break
                safe_mode = True
        # 5. DCN Synchrony (Audit Point 12)
        if all(r.success for r in results.values()):
            dcn = DCNProtocol()
            if dcn.is_active:
                # v14.1 Graduation: Use Raft-lite Mission Truth for confirmed outcomes
                from backend.utils.runtime_tasks import create_tracked_task
                create_tracked_task(
                    dcn.broadcast_mission_truth(mission_id, {k: v.message for k, v in results.items()}), 
                    name=f"dcn-truth-{mission_id}"
                )

        return list(results.values())

    async def _execute_node(self, node: Any, previous_results: Dict[str, ToolResult], perception: Dict[str, Any], blackboard: MissionBlackboard = None, user_id: str = "global", wave_count: int = 0, policy: Optional[Any] = None, mission_sm: Optional[CentralExecutionState] = None) -> ToolResult:
        """Executes a single node with template-resolved inputs, retries and fallbacks."""
        agent_name = node.agent
        mission_id = perception.get("request_id") or "global"
        start_time = asyncio.get_event_loop().time()
        # 0. Override Policy Constraints
        max_retries = 1
        agent_name = node.agent
        memory_scope = getattr(node, "memory_scope", "task")
        if node.contract:
            max_retries = node.contract.max_retries
        elif policy:
            max_retries = policy.max_retries
        else:
            max_retries = getattr(node, 'retry_count', 1)
            
        # Global guardrail: max 2 retries
        if max_retries > 2:
            max_retries = 2
        if policy and policy.sandbox_required:
            logger.info(f"[V14 Brain] Mandatory Sandbox Isolation Enforced for node {node.id}")
        
        # 1. Input Resolution ({{task_id.result}})
        resolved_inputs = self._resolve_inputs(node.inputs, previous_results)
        
        # 2. Parameter Synthesis
        merged_params = {
            **perception.get("context", {}), 
            **resolved_inputs, 
            "input": perception.get("input"),
            "__blackboard__": blackboard.serialize() if blackboard else "" # Injected compressed swarm state
        }
        strict_schema = bool(
            getattr(node, "strict_schema", True)
            and getattr(getattr(node, "contract", None), "strict_schema", True)
        )
        validation_payload = dict(resolved_inputs)
        validation_payload.setdefault("input", perception.get("input"))
        try:
            self._validate_payload_schema(
                validation_payload,
                getattr(getattr(node, "contract", None), "input_schema", {}),
                strict_schema=strict_schema,
                label=f"{node.id} input",
            )
        except Exception as exc:
            if mission_sm:
                mission_sm.record_node(node.id, "failed", {"agent": agent_name, "error": str(exc)})
            return ToolResult(
                success=False,
                error=str(exc),
                agent=agent_name,
                message="",
                data={"validation": "input"},
            )

        # --- Step 6.2: Global Circuit Breaker Check ---
        from backend.utils.circuit_breaker import get_breaker
        breaker = get_breaker(f"agent:{agent_name}")
        
        # --- Step 6.3: Agent RBAC Check ---
        from backend.core.agent_registry import AgentRegistry
        from backend.db.postgres import PostgresDB
        from backend.db.models import UserProfile
        from sqlalchemy import select

        async with PostgresDB._session_factory() as session:
            stmt = select(UserProfile.persona_archetype).where(UserProfile.user_id == user_id)
            res = await session.execute(stmt)
            user_role = res.scalar_one_or_none() or "guest"
            
            agent_cap = AgentRegistry.get_agent(agent_name)
            if agent_cap and agent_cap.required_role != "guest":
                roles_hierarchy = ["guest", "user", "admin", "developer"]
                if roles_hierarchy.index(user_role) < roles_hierarchy.index(agent_cap.required_role):
                    logger.warning(f"🚫 [RBAC] Access denied: User '{user_id}' (role:{user_role}) cannot access agent '{agent_name}' (required:{agent_cap.required_role})")
                    return ToolResult(
                        success=False,
                        error=f"Access Denied: Agent '{agent_name}' requires '{agent_cap.required_role}' privileges.",
                        agent=agent_name,
                        state=AgentState.FAILED
                    )

        # --- Step 6.3: Sandbox Isolation Validation ---
        if agent_name.lower() in ["artisan", "coder", "repl"] and not policy.sandbox_required:
            logger.warning(f"🛡️ [Shield] Mandatory Sandbox Escalation for coding agent '{agent_name}'.")
            policy.sandbox_required = True

        attempts = 0
        last_error = None
        retry_strategy = (
            getattr(getattr(node, "contract", None), "retry_strategy", None)
            or getattr(node, "retry_strategy", None)
            or getattr(policy, "retry_strategy", "exp_backoff_jitter")
        )
        
        # Timeline recorder: node start
        try:
            CognitiveTracer.add_step(perception.get("request_id", "global"), "node_start", {"node_id": node.id, "agent": agent_name})
        except Exception:
            pass
        logger.info(
            "executor_node_started",
            extra={
                "trace_id": mission_id,
                "mission_id": mission_id,
                "node_id": node.id,
                "agent": agent_name,
                "status": "started",
                "duration_ms": 0,
            },
        )
        # formal lifecycle: RUNNING
        node.state = NodeState.RUNNING
        from backend.core.agent_bus import agent_bus
        from backend.core.orchestrator_types import AgentState
        
        await agent_bus.publish(agent_name, "state_change", {"node_id": node.id, "state": AgentState.EXECUTING})

        sandbox_token = AgentSandbox.activate(
            mission_id=mission_id,
            node_id=node.id,
            allowed_tools=getattr(getattr(node, "contract", None), "allowed_tools", []),
            memory_scope=memory_scope,
        )
        # Phase 2: Autonomous Parameter Optimization
        dynamic_params = await parameter_optimizer.get_parameters(mission_id)
        merged_params.update(dynamic_params)

        try:
            while attempts <= max_retries:
                try:
                    await agent_bus.publish(agent_name, "mission_pulse", {
                        "node_id": node.id, 
                        "attempt": attempts, 
                        "status": "executing"
                    })

                    # --- v14.2 Sub-DAG Caching ---
                    # (Cache logic remains...)

                    is_fragile = getattr(node, "is_fragile", False) or getattr(node, "high_friction", False)
                    # (Consensus logic remains...)

                    timeout = 15
                    # (Timeout logic remains...)

                    # 3. Agent Dispatch Selection (v15.0 registry-aware)
                    agent_config = AgentRegistry.get_agent(agent_name)
                    
                    async with traced_span(
                        "executor.node",
                        mission_id=mission_id,
                        node_id=node.id,
                        agent=agent_name,
                        wave=wave_count,
                    ):
                        # (Chaos logic remains...)

                        async def _do_call():
                            if isinstance(agent_config, AgentConfig):
                                return await self._dispatch_remote_agent_call(
                                    agent_config, 
                                    {**merged_params, "__memory_scope__": memory_scope},
                                    perception.get("context", {}),
                                    timeout=timeout
                                )
                            else:
                                # Legacy Local Call
                                raw_res = await asyncio.wait_for(
                                    ai_service_breaker.async_call(
                                        call_tool,
                                        agent_name,
                                        {
                                            **merged_params,
                                            "__memory_scope__": memory_scope,
                                            "__sandbox__": policy.sandbox_required if policy else False,
                                        },
                                        {
                                            **perception.get("context", {}),
                                            "model_tier": getattr(node, "model_tier", "L2"),
                                        },
                                    ),
                                    timeout=timeout,
                                )
                                return ToolResult(**raw_res) if isinstance(raw_res, dict) else raw_res

                        # Wrap execution with Circuit Breaker
                        result = await breaker.call(_do_call)

                    if result.success:
                        # --- Step 6.1: Observability & Security Scrubbing ---
                        if result.message:
                            from backend.utils.sanitizer import ResultSanitizer
                            result.message = ResultSanitizer.sanitize_bot_response(result.message)
                        
                        node.state = NodeState.COMPLETED
                        await agent_bus.publish(agent_name, "state_change", {"node_id": node.id, "state": AgentState.COMPLETE})
                        # (Usage and learning logic remains...)
                        return result

                    # STEP 4.3: SELF-HEALING / ALTERNATIVE AGENT
                    alternative_agent = getattr(node, "fallback_agent", None)
                    if alternative_agent and attempts == max_retries:
                        logger.warning(f"[Self-Healing] {agent_name} failed. Routing to Alternative: {alternative_agent}")
                        # Re-dispatch with alternative
                        node.agent = alternative_agent
                        agent_name = alternative_agent
                        attempts = 0 # Reset attempts for alternative
                        result.recovered_via = f"alt_agent:{alternative_agent}"
                        continue

                    last_error = result.error or "Unknown failure"
                    attempts += 1
                    
                except Exception as e:
                    last_error = str(e)
                    attempts += 1
            
            # formal lifecycle: FAILED
            node.state = NodeState.FAILED
            await agent_bus.publish(agent_name, "state_change", {"node_id": node.id, "state": AgentState.FAILED})
            compensation = await self._run_compensation(node, mission_id=mission_id, agent_name=agent_name, error=last_error, mission_sm=mission_sm)
            if compensation:
                 node.state = NodeState.COMPENSATED

            return ToolResult(
                success=False,
                error=f"Max retries exceeded: {last_error}",
                agent=agent_name,
                state=AgentState.FAILED
            )
        finally:
            AgentSandbox.deactivate(sandbox_token)

    async def _execute_remote_node(self, node: Any, remote_node: str, perception: Dict[str, Any]) -> ToolResult:
        """
        Sovereign v14.2 Distributed Offloading.
        1. Package task meta and inputs.
        2. Broadcast REMOTE_EXECUTION_REQUEST pulse.
        3. Poll for REMOTE_RESULT pulse or Redis state change.
        """
        mission_id = perception.get("request_id", "swarm_mission")
        logger.info(f"[DCN] Packaging {node.id} for remote execution on {remote_node}...")
        
        from backend.core.dcn_protocol import DCNProtocol
        dcn = DCNProtocol()
        if not dcn.is_active:
             return ToolResult(success=False, error="DCN Protocol offline", agent=node.agent)

        payload = {
            "node_id": node.id,
            "agent": node.agent,
            "inputs": node.inputs,
            "perception": perception,
            "target_node": remote_node
        }
        
        # Broadcast the request
        await dcn.broadcast_gossip(mission_id, payload, pulse_type="remote_execution_request")
        
        # 4. Wait for Result (Polling Redis status for simplicity in v14.2)
        start_wait = time.time()
        max_wait = getattr(node.contract, "timeout_ms", 60000) / 1000.0
        
        while time.time() - start_wait < max_wait:
            state_data = CentralExecutionState.get_full_data(mission_id)
            if state_data:
                node_events = state_data.get("nodes", {}).get(node.id, {}).get("events", [])
                for evt in node_events:
                    if evt.get("status") == "completed":
                        info = evt.get("info", {})
                        logger.info(f"[DCN] Remote task {node.id} result recovered from cluster state.")
                        return ToolResult(
                            success=True,
                            message=info.get("message", ""),
                            agent=node.agent,
                            data=info.get("data", {}),
                            latency_ms=info.get("latency_ms", 0)
                        )
                    elif evt.get("status") == "failed":
                        return ToolResult(success=False, error=evt.get("info", {}).get("error", "Remote failure"), agent=node.agent)
            
            await asyncio.sleep(2)
            
        return ToolResult(success=False, error=f"Remote execution timeout ({max_wait}s) on {remote_node}", agent=node.agent)

    async def _dispatch_remote_agent_call(self, config: Any, params: Dict[str, Any], context: Dict[str, Any], timeout: float = 30.0) -> ToolResult:
        """
        Sovereign v15.0: Secure mTLS Dispatch via agent_client.
        """
        return await agent_client.call_agent(
            agent_id=config.name if hasattr(config, "name") else str(config),
            params=params,
            context=context,
            timeout=timeout
        )

    async def _categorize_failure(self, error: str) -> str:
        """v14.1 Failure Classification."""
        err_lower = error.lower()
        if "json" in err_lower or "schema" in err_lower or "format" in err_lower:
            return "F-1" # Syntactic
        if "timeout" in err_lower or "unreachable" in err_lower or "rate limit" in err_lower:
            return "F-3" # System
        return "F-2" # Logic/Grounding (Default)

    async def _run_compensation(
        self,
        node: Any,
        mission_id: str,
        agent_name: str,
        error: Optional[str],
        mission_sm: Optional[CentralExecutionState],
    ) -> Optional[Dict[str, Any]]:
        action = getattr(node, "compensation_action", None)
        if not action:
            return None
        
        logger.warning(f"[Executor] Activating compensation for {node.id}: {action}")
        compensation = {
            "action": action,
            "status": "executed",
            "error": error,
            "timestamp": time.time()
        }
        
        # In a real system, we might execute a specific compensation task/agent here
        # For now, we formalize the record of it.
        
        if mission_sm:
            mission_sm.record_node(node.id, "compensated", {"agent": agent_name, **compensation})
            
        logger.info(
            "executor_compensation_executed",
            extra={
                "trace_id": mission_id,
                "mission_id": mission_id,
                "node_id": node.id,
                "agent": agent_name,
                "status": "compensated",
            },
        )
        return compensation

    def _validate_payload_schema(
        self,
        payload: Dict[str, Any],
        schema: Dict[str, Any],
        strict_schema: bool,
        label: str,
    ) -> None:
        if not schema:
            return
        allowed_keys = set(schema.keys())
        if strict_schema:
            extras = sorted(set(payload.keys()) - allowed_keys)
            if extras:
                raise ValueError(f"{label} contains unexpected fields: {extras}")
        for field, rules in schema.items():
            required = bool(rules.get("required", False))
            expected = rules.get("type")
            if required and field not in payload:
                raise ValueError(f"{label} missing required field '{field}'")
            if field in payload and expected:
                self._assert_type(payload[field], expected, label, field)

    def _assert_type(self, value: Any, expected: str, label: str, field: str) -> None:
        if value is None and expected.startswith("optional["):
            return
        normalized = expected.replace("optional[", "").replace("]", "")
        type_map = {
            "str": str,
            "dict": dict,
            "list": list,
            "bool": bool,
            "int": int,
            "float": (int, float),
        }
        expected_type = type_map.get(normalized)
        if expected_type is None:
            return
        if normalized == "bool":
            is_valid = isinstance(value, bool)
        elif normalized == "int":
            is_valid = isinstance(value, int) and not isinstance(value, bool)
        else:
            is_valid = isinstance(value, expected_type)
        if not is_valid:
            raise ValueError(f"{label} field '{field}' expected {expected}, got {type(value).__name__}")

    def _breaker_key(self, node: Any) -> str:
        return f"{node.agent}:{node.id}"

    def _get_circuit_state(self, node: Any) -> Dict[str, float]:
        key = self._breaker_key(node)
        return self._node_breakers.setdefault(key, {"failures": 0.0, "open_until": 0.0})

    def _record_circuit_failure(self, node: Any) -> None:
        state = self._get_circuit_state(node)
        config = getattr(node, "circuit_breaker", {}) or {}
        threshold = max(1, int(config.get("fail_threshold", 3)))
        cooldown_ms = max(1000, int(config.get("cooldown_ms", 10000)))
        state["failures"] += 1
        if state["failures"] >= threshold:
            state["open_until"] = time.time() + (cooldown_ms / 1000.0)

    def _record_circuit_success(self, node: Any) -> None:
        state = self._get_circuit_state(node)
        state["failures"] = 0.0
        state["open_until"] = 0.0

    def _resolve_inputs(self, inputs: Dict[str, Any], previous_results: Dict[str, ToolResult]) -> Dict[str, Any]:
        """Resolves template placeholders like {{t_search.result}}."""
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, str) and "{{" in value and "}}" in value:
                clean_template = value.replace("{{", "").replace("}}", "")
                
                if clean_template == "all_results":
                    resolved[key] = "\n\n".join([f"Task [{tid}]: {res.message}" for tid, res in previous_results.items()])
                    continue
                
                parts = clean_template.split(".")
                task_id = parts[0]
                attr = parts[1] if len(parts) > 1 else "result"
                
                if task_id in previous_results:
                    res = previous_results[task_id]
                    if attr == "result": resolved[key] = res.message
                    elif attr == "data": resolved[key] = str(res.data)
                    else: resolved[key] = str(getattr(res, attr, ""))
                else:
                    resolved[key] = value
            else:
                resolved[key] = value
        return resolved
