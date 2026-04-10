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
from enum import Enum
from ..orchestrator_types import ToolResult, IntentResult, AgentResult
from ..tool_registry import call_tool
from ..blackboard import MissionBlackboard
from backend.broadcast_utils import SovereignBroadcaster, PULSE_NODE_COMPLETED
from ...utils.network import ai_service_breaker
from ...celery_app import celery_app
from ...agents.registry import AGENT_REGISTRY
from ...agents.consensus_agent import ConsensusAgentV11
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
from backend.services.billing_service import billing_service


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

    def __init__(self):
        self._node_breakers: Dict[str, Dict[str, float]] = {}
        self._wave_lock = asyncio.Lock()

    async def execute(self, graph: Any, perception: Dict[str, Any], user_id: str = "global", policy: Optional[Any] = None, safe_mode: bool = False) -> List[ToolResult]:


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
        
        while remaining_nodes or running_tasks:
            # 1. Mission Cancellation Check
            from backend.utils.mission import MissionControl
            if MissionControl.is_cancelled(mission_id):
                logger.warning(f"[V14.1 Executor] Mission {mission_id} cancelled. Aborting...")
                for t in running_tasks: t.cancel()
                break

            # 2. Identify and Schedule Executable Nodes
            async with self._wave_lock:
                executable_nodes = [
                    n for n in remaining_nodes
                    if all(dep in completed_ids for dep in n.dependencies)
                ]
            
            # Constraint check (Parallelism & Budget)
            snapshot = capture_resource_pressure(vram_pressure=False, queue_depth=len(remaining_nodes))
            pressure_factor = 1.0
            if "vram" in snapshot.active_dimensions or "ram" in snapshot.active_dimensions:
                pressure_factor = 0.5
            if "cpu" in snapshot.active_dimensions:
                pressure_factor = 0.25
            
            base_parallel = policy.parallel_waves if policy else 4
            max_parallel = 1 if safe_mode else max(1, int(base_parallel * pressure_factor))
            
            if pressure_factor < 1.0:
                logger.warning(f"[Executor] Resource pressure detected ({snapshot.active_dimensions}). Throttling concurrency to {max_parallel}.")
            
            slots_available = max_parallel - len(running_tasks)
            
            if slots_available > 0 and executable_nodes:
                nodes_to_start = executable_nodes[:slots_available]
                for node in nodes_to_start:
                    if budget_tracker.remaining_tool_calls() <= 0:
                        logger.error("[Shield] Tool budget exhausted.")
                        break
                    
                    # formal lifecycle: SCHEDULED
                    node.state = NodeState.SCHEDULED
                    task = asyncio.create_task(
                        self._execute_node(node, results, perception, blackboard=blackboard, user_id=user_id, wave_count=wave_count, policy=policy, mission_sm=mission_sm)
                    )
                    running_tasks[task] = node
                    remaining_nodes.remove(node)
                    budget_tracker.reserve_tool_calls(1)
                    total_nodes_executed += 1
                    logger.debug(f"[Executor] Scheduled node {node.id}")

            if not running_tasks:
                if remaining_nodes:
                    logger.error(f"[V14.1 Executor] Deadlock detected. Remaining: {[n.id for n in remaining_nodes]}")
                break

            # 3. Wait for any task to complete
            done, _ = await asyncio.wait(running_tasks.keys(), return_when=asyncio.FIRST_COMPLETED)
            
            for task in done:
                node = running_tasks.pop(task)
                try:
                    res = await task
                    results[node.id] = res
                    completed_ids.add(node.id)
                    
                    # v14.1 Compensation & Refund Logic
                    if not res.success and node.critical:
                        logger.warning(f"[V14.1 Executor] Critical failure on {node.id}")
                        
                        # Partial Refund for System failures
                        failure_type = self._categorize_failure(res.error or "Unknown")
                        if failure_type == "F-3": # System/Infra
                             refund_amount = 0.8 * 5.0 # 80% of autonomous cost
                             logger.info(f"[Billing] Triggering partial refund ({refund_amount} credits) for system failure.")
                             await billing_service.add_credits(user_id, amount=refund_amount)
                        
                        if not safe_mode:
                            logger.info("[Resilience] Escalating to Safe Mode (Linear).")
                            safe_mode = True
                        else:
                            # Already in safe mode and failed critical node -> ROLLBACK
                            logger.error("[Resilience] Safe mode exhausted. Triggering Compensation Rollback.")
                            await compensation_coordinator.compensate()
                            break
                    
                    # Update budget
                    budget_tracker.add_tokens(node.agent, getattr(res, "total_tokens", 0))
                    
                except Exception as e:
                    logger.error(f"[Executor] Task crash for {node.id}: {e}")
                    results[node.id] = ToolResult(success=False, error=str(e), agent=node.agent)
                    completed_ids.add(node.id)

            # Safeguard
            if total_nodes_executed > self.MAX_MISSION_NODES:
                results[n.id] = res
                completed_ids.add(n.id)
                remaining_nodes.remove(n)
                if not budget_tracker.add_tokens(n.agent, getattr(res, "total_tokens", 0)):
                    logger.error(
                        "[Shield] Mission %s aborted: Token limit (%s) reached.",
                        mission_id,
                        getattr(policy.budget, "token_limit", 0) if policy and getattr(policy, "budget", None) else 0,
                    )
                    MetricsHub.reject_budget("tokens")
                    return list(results.values())
                
            # 4. Critical Path Failure Check
            critical_failure = False
            for n in nodes_to_run:
                res = results[n.id]
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

        circuit_state = self._get_circuit_state(node)
        if circuit_state["open_until"] > time.time():
            remaining_ms = int((circuit_state["open_until"] - time.time()) * 1000)
            message = f"Circuit open for node {node.id}; cooldown active for {remaining_ms}ms"
            if mission_sm:
                mission_sm.record_node(node.id, "circuit_open", {"agent": agent_name, "cooldown_ms": remaining_ms})
            return ToolResult(
                success=False,
                error=message,
                agent=agent_name,
                message=getattr(node, "fallback_output", {}).get("message", ""),
                data={"circuit_breaker": dict(getattr(node, "circuit_breaker", {}))},
                retryable=True,
            )

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
        sandbox_token = AgentSandbox.activate(
            mission_id=mission_id,
            node_id=node.id,
            allowed_tools=getattr(getattr(node, "contract", None), "allowed_tools", []),
            memory_scope=memory_scope,
        )
        try:
            while attempts <= max_retries:
                try:
                    attempts += 1

                    if not await check_agent_limit(user_id, agent_name, limit=60):
                        return ToolResult(
                            success=False,
                            error=f"Sovereign Rate Limit Exceeded for agent '{agent_name}'. Please wait before next mission.",
                            agent=agent_name,
                        )

                    is_fragile = getattr(node, "is_fragile", False) or getattr(node, "high_friction", False)
                    if is_fragile and attempts == 1:
                        logger.info(f"[V8 Swarm] Mission Fragility Detected for node {node.id}. Activating Consensus Adjudication.")
                        swarm_tasks = [
                            ai_service_breaker.async_call(call_tool, agent_name, merged_params, perception.get("context", {})),
                            ai_service_breaker.async_call(call_tool, "Critic", merged_params, perception.get("context", {})),
                            ai_service_breaker.async_call(call_tool, "Optimizer", merged_params, perception.get("context", {})),
                        ]
                        candidate_results = await asyncio.gather(*swarm_tasks, return_exceptions=True)
                        valid_candidates = []

                        for cr in candidate_results:
                            if isinstance(cr, Exception):
                                continue
                            if isinstance(cr, dict):
                                valid_candidates.append(
                                    AgentResult(**cr) if "success" in cr else AgentResult(success=True, message=str(cr), agent="unknown")
                                )
                            elif isinstance(cr, ToolResult):
                                valid_candidates.append(cr)
                            else:
                                valid_candidates.append(cr)

                        consensus_agent = ConsensusAgentV11()
                        from ...agents.consensus_agent import ConsensusInput, FidelityRubric

                        candidate_rubrics = [
                            FidelityRubric(
                                syntax_correctness=getattr(c, "syntax_score", 0.9),
                                logical_consistency=getattr(c, "logic_score", 0.8),
                                factual_grounding=getattr(c, "grounding_score", 0.85),
                                sovereign_resonance=getattr(c, "resonance_score", 0.9),
                            )
                            for c in valid_candidates
                        ]

                        consensus_res = await consensus_agent.execute(
                            ConsensusInput(
                                goal=perception.get("input", "Synchronous mission"),
                                candidates=valid_candidates,
                                rubrics=candidate_rubrics,
                                context=perception.get("context", {}),
                            )
                        )

                        if consensus_res.success:
                            winner_data = consensus_res.data.get("winner", {})
                            result = ToolResult(
                                success=True,
                                message=winner_data.get("message", "Consensus selected winner."),
                                agent=winner_data.get("agent", agent_name),
                                data=winner_data.get("data", {}),
                                fidelity_score=consensus_res.fidelity_score,
                            )
                        else:
                            result = valid_candidates[0] if valid_candidates else ToolResult(success=False, error="Swarm failure", agent=agent_name)

                    timeout = 15
                    if node.contract and node.contract.timeout_ms:
                        timeout = node.contract.timeout_ms / 1000.0
                    elif policy and getattr(policy, "budget", None):
                        timeout = policy.budget.cpu_time_limit_ms / 1000.0

                    logger.debug(f"[TEC] Executing {node.id} with timeout={timeout}s, scope={memory_scope}")

                    async with traced_span(
                        "executor.node",
                        mission_id=mission_id,
                        node_id=node.id,
                        agent=agent_name,
                        wave=wave_count,
                    ):
                        if ChaosMonkey.is_enabled():
                            if os.getenv("CHAOS_AGENT_TIMEOUT", "").lower() == agent_name.lower():
                                await ChaosMonkey.simulate_agent_timeout(agent_name, timeout_ms=int(timeout * 1000))
                            if os.getenv("CHAOS_TOOL_CRASH", "").lower() == agent_name.lower():
                                ChaosMonkey.simulate_tool_crash(agent_name, failure_rate=1.0)
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
                                    "trace_id": mission_id,
                                    "mission_id": mission_id,
                                    "node_id": node.id,
                                    "request_id": mission_id,
                                },
                            ),
                            timeout=timeout,
                        )

                    if not isinstance(raw_res, ToolResult):
                        result = ToolResult(**raw_res) if isinstance(raw_res, dict) else ToolResult(success=True, message=str(raw_res), agent=agent_name)
                    else:
                        result = raw_res
                    self._validate_payload_schema(
                        result.model_dump(),
                        getattr(getattr(node, "contract", None), "output_schema", {}),
                        strict_schema=strict_schema,
                        label=f"{node.id} output",
                    )

                    if result.success:
                        self._record_circuit_success(node)
                        result.latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                        result.message = ResultSanitizer.sanitize_bot_response(result.message or "")

                        prompt_tokens = getattr(result, "prompt_tokens", 0)
                        completion_tokens = getattr(result, "completion_tokens", 0)
                        calculated_cu = 1.0 + (prompt_tokens + completion_tokens) / 1000.0

                        try:
                            async with PostgresDB._session_factory() as session:
                                usage = CognitiveUsage(
                                    mission_id=mission_id,
                                    user_id=user_id,
                                    agent=agent_name,
                                    prompt_tokens=prompt_tokens,
                                    completion_tokens=completion_tokens,
                                    latency_ms=result.latency_ms,
                                    cu_cost=calculated_cu,
                                )
                                session.add(usage)
                                await session.commit()
                        except Exception as e:
                            logger.error(f"[V13.1 Executor] Failed to log CU usage: {e}")

                        if isinstance(result.data, dict) and "blackboard_update" in result.data:
                            for k, v in result.data["blackboard_update"].items():
                                blackboard.add_artifact(k, v)

                        if hasattr(result, "insight") and result.insight:
                            blackboard.update_insight(agent_name, result.insight)

                        SovereignBroadcaster.publish(PULSE_NODE_COMPLETED, {
                            "node_id": node.id,
                            "agent": agent_name,
                            "success": True,
                            "latency": result.latency_ms,
                            "fidelity": getattr(result, 'fidelity_score', 0.0),
                            "current_wave": wave_count
                        }, user_id=user_id)

                        if mission_sm:
                            mission_sm.record_node(node.id, "completed", {"agent": agent_name, "latency_ms": result.latency_ms})
                        try:
                            CognitiveTracer.add_step(perception.get("request_id", "global"), "node_complete", {"node_id": node.id, "agent": agent_name, "latency_ms": result.latency_ms})
                        except Exception:
                            pass
                        MetricsHub.observe_node(agent_name, node.id, result.latency_ms)
                        MetricsHub.record_tool_call(agent_name)
                        logger.info(
                            "executor_node_completed",
                            extra={
                                "trace_id": mission_id,
                                "mission_id": mission_id,
                                "node_id": node.id,
                                "agent": agent_name,
                                "status": "success",
                                "duration_ms": int(result.latency_ms),
                            },
                        )
                        # formal lifecycle: COMPLETED
                        node.state = NodeState.COMPLETED
                        
                        # Register for potential compensation
                        if hasattr(node, "reversal_logic") and node.reversal_logic:
                            compensation_coordinator.register_step(
                                node.id, 
                                node.agent, 
                                node.reversal_logic, 
                                getattr(node, "reversal_params", {})
                            )
                        
                        return result

                    last_error = result.error or "Unknown failure"
                    self._record_circuit_failure(node)
                    logger.warning(f"[V8 Executor] Agent {agent_name} failed (Attempt {attempts}/{max_retries+1}): {last_error}")

                except asyncio.TimeoutError:
                    last_error = f"Timeout ({timeout}s)"
                    self._record_circuit_failure(node)
                    logger.error(f"[V8 Executor] Agent {agent_name} timed out.")
                except Exception as e:
                    last_error = str(e)
                    self._record_circuit_failure(node)
                    logger.exception(f"[V8 Executor] Agent {agent_name} crashed: {e}")

                if attempts <= max_retries:
                    # v14.1 Adaptive Retry Categorization
                    failure_type = self._categorize_failure(last_error)
                    logger.info(f"[Retry] Failure categorized as {failure_type}. Adjusting strategy.")
                    
                    if failure_type == "F-1": # Syntactic: Immediate retry
                        delay = 0.5
                    elif failure_type == "F-2": # Logic: Reasoning Refinement might be needed, but we retry first with high temperature?
                        # For now, standard backoff but flag for refinement
                        delay = compute_backoff_delay(attempts, retry_strategy)
                    else: # F-3 System/Timeout: Exponential backoff with jitter
                        delay = compute_backoff_delay(attempts, retry_strategy)
                        
                    await asyncio.sleep(delay)
                    
    async def _categorize_failure(self, error: str) -> str:
        """v14.1 Failure Classification."""
        err_lower = error.lower()
        if "json" in err_lower or "schema" in err_lower or "format" in err_lower:
            return "F-1" # Syntactic
        if "timeout" in err_lower or "unreachable" in err_lower or "rate limit" in err_lower:
            return "F-3" # System
        return "F-2" # Logic/Grounding (Default)
        # formal lifecycle: FAILED
        node.state = NodeState.FAILED
        compensation = await self._run_compensation(node, mission_id=mission_id, agent_name=agent_name, error=last_error, mission_sm=mission_sm)
        if compensation:
             node.state = NodeState.COMPENSATED

        if mission_sm:
            mission_sm.record_node(node.id, "failed", {"agent": agent_name, "error": last_error})
            
        fallback_output = getattr(node, "fallback_output", None) or {}
        logger.error(
            "executor_node_failed",
            extra={
                "trace_id": mission_id,
                "mission_id": mission_id,
                "node_id": node.id,
                "agent": agent_name,
                "status": "failed",
                "duration_ms": int((asyncio.get_event_loop().time() - start_time) * 1000),
            },
        )
        return ToolResult(
            success=False,
            error=f"Max retries exceeded: {last_error}",
            agent=agent_name,
            message=fallback_output.get("message", ""),
            data={
                "fallback_output": fallback_output,
                "compensation_action": getattr(node, "compensation_action", None),
                "compensation": compensation,
            },
        )

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
