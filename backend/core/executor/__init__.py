"""
Sovereign Execution Engine v8.
Executes the Task Graph (DAG) for cognitive missions.
Handles parallelization, dependency resolution, and agent coordination.
"""

import logging
import asyncio
import json
import os
import time
from typing import Dict, Any, List, Set, Optional
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


logger = logging.getLogger(__name__)

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
        budget = getattr(policy, "budget", None)
        budget_tracker = ExecutionBudgetTracker(
            token_limit=getattr(budget, "token_limit", 200000),
            tool_call_limit=getattr(budget, "tool_call_limit", 20),
        )

        
        while remaining_nodes:
            # 1. Mission Cancellation Check
            from backend.utils.mission import MissionControl
            mission_id = perception.get("request_id") or "global"
            if MissionControl.is_cancelled(mission_id):
                logger.warning(f"[V8 Executor] Mission {mission_id} cancelled by user. Aborting...")
                break

            # 2. Identify executable nodes (all deps satisfied)
            async with self._wave_lock:
                executable_nodes = [
                    n for n in remaining_nodes
                    if all(dep in completed_ids for dep in n.dependencies)
                ]
            
            if not executable_nodes:
                if remaining_nodes:
                    logger.error(
                        "[V8 Executor] Dependency deadlock in graph. Remaining=%s completed=%s",
                        [n.id for n in remaining_nodes],
                        sorted(completed_ids),
                    )
                break
            
            # Audit Point 07: Execution Guards
            wave_count += 1
            if wave_count > self.MAX_WAVES:
                logger.error(f"[Shield] Mission {mission_id} aborted: Wave limit ({self.MAX_WAVES}) exceeded.")
                SovereignBroadcaster.publish("MISSION_ABORTED", {"reason": "wave_limit_exceeded"}, user_id=user_id)
                break

            logger.debug("[V13.1 Executor] Executing Wave %d: %s", wave_count, [n.id for n in executable_nodes])
            
            # 2. Parallel Execution of Wave (Limited by Policy)
            max_parallel = 1 if safe_mode else (policy.parallel_waves if policy else len(executable_nodes))
            queue_depth = len(remaining_nodes)
            pressure = capture_resource_pressure(vram_pressure=False, queue_depth=queue_depth)
            try:
                if HAS_REDIS:
                    vram_pressure = await redis_client.get("vram:pressure")
                    pressure = capture_resource_pressure(
                        vram_pressure=bool(vram_pressure and str(vram_pressure).lower() == "true"),
                        queue_depth=queue_depth,
                    )
                    if pressure.vram_pressure:
                        max_parallel = max(1, min(max_parallel, 1))
            except Exception:
                pass
            if "cpu" in pressure.active_dimensions or "ram" in pressure.active_dimensions:
                max_parallel = max(1, min(max_parallel, 1))
            if "queue" in pressure.active_dimensions:
                max_parallel = max(1, min(max_parallel, 2))
            if budget_tracker.remaining_tool_calls() <= 0:
                logger.error("[Shield] Mission %s aborted: Tool call budget exhausted before scheduling.", mission_id)
                MetricsHub.reject_budget("tool_calls")
                break
            max_parallel = min(max_parallel, budget_tracker.remaining_tool_calls())
            nodes_to_run = executable_nodes[:max_parallel]
            MetricsHub.observe_wave(len(nodes_to_run), queue_depth)
            
            total_nodes_executed += len(nodes_to_run)
            
            if total_nodes_executed >= self.WARNING_THRESHOLD and total_nodes_executed < self.MAX_MISSION_NODES:
                logger.warning(f"[V13.1 Executor] Mission {mission_id} reaching complexity threshold ({total_nodes_executed} nodes).")
                SovereignBroadcaster.publish("MISSION_WARNING", {"nodes_count": total_nodes_executed, "message": "High complexity mission detected. Approaching safety limit."}, user_id=user_id)

            if total_nodes_executed > self.MAX_MISSION_NODES:
                logger.error(f"[Shield] Mission {mission_id} aborted: Node limit ({self.MAX_MISSION_NODES}) exceeded.")
                SovereignBroadcaster.publish("MISSION_ABORTED", {"reason": "node_limit_exceeded"}, user_id=user_id)
                break

            tasks = [self._execute_node(n, results, perception, blackboard=blackboard, user_id=user_id, wave_count=wave_count, policy=policy, mission_sm=mission_sm) for n in nodes_to_run]
            budget_tracker.reserve_tool_calls(len(nodes_to_run))
            SovereignBroadcaster.publish("WAVE_STARTED", {"nodes": [n.id for n in nodes_to_run], "current_wave": wave_count}, user_id=user_id)

            # --- Distributed Wave Management (v2.0-Hardened) ---
            try:
                if (
                    os.getenv("DISTRIBUTED_MODE", "false").lower() == "true"
                    and os.getenv("CHAOS_REDIS_OUTAGE", "false").lower() != "true"
                    and HAS_REDIS
                ):
                    from .distributed import DistributedGraphExecutor
                    dist_executor = DistributedGraphExecutor(redis_client)
                    
                    # 1. Enqueue Wave
                    previous_results_serializable = {k: v.model_dump() for k, v in results.items()}
                    await dist_executor.enqueue_wave(mission_id, nodes_to_run, perception, previous_results_serializable)
                    
                    # 2. Reactive Result Management (v2.1-Hardened)
                    pubsub = redis_client.pubsub()
                    event_channel = f"dcn:mission:{mission_id}:events"
                    await pubsub.subscribe(event_channel)
                    
                    pending_node_ids = set(n.id for n in nodes_to_run)
                    wave_results_map = {}
                    
                    # Audit Point: Pre-check for results before long-wait subscription
                    for node_id in list(pending_node_ids):
                        result_key = f"dcn:mission:{mission_id}:result:{node_id}"
                        cached_res = await redis_client.get(result_key)
                        if cached_res:
                            wave_results_map[node_id] = ToolResult(**json.loads(cached_res))
                            pending_node_ids.remove(node_id)

                    # Reactive Wait Loop
                    start_time = asyncio.get_event_loop().time()
                    timeout = 120 
                    
                    try:
                        while pending_node_ids and (asyncio.get_event_loop().time() - start_time) < timeout:
                            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                            if message and message["type"] == "message":
                                data = json.loads(message["data"])
                                event_type = data.get("event")
                                tgt_node_id = data.get("node_id")
                                
                                if event_type == "node_complete" and tgt_node_id in pending_node_ids:
                                    result_key = f"dcn:mission:{mission_id}:result:{tgt_node_id}"
                                    cached_res = await redis_client.get(result_key)
                                    if cached_res:
                                        wave_results_map[tgt_node_id] = ToolResult(**json.loads(cached_res))
                                        pending_node_ids.remove(tgt_node_id)
                                
                                elif event_type == "node_failed" and tgt_node_id in pending_node_ids:
                                    logger.warning(f"⚠️ [DCN] Node {tgt_node_id} reported failure. Re-evaluating...")
                                    # For v2.1: Simple reactive retry or fallback can be triggered here
                                    # Currently, we just let the loop continue or break if critical
                                    pass
                    finally:
                        await pubsub.unsubscribe(event_channel)
                        await pubsub.close()
                    
                    if pending_node_ids:
                        logger.error(f"🚨 [DCN] Wave timeout. Missing: {pending_node_ids}. Attempting LOCAL FALLBACK...")
                        # Partial local fallback for timed-out nodes
                        timeout_nodes = [n for n in nodes_to_run if n.id in pending_node_ids]
                        fallback_tasks = [self._execute_node(n, results, perception, blackboard=blackboard, user_id=user_id, wave_count=wave_count) for n in timeout_nodes]
                        fallback_results = await asyncio.gather(*fallback_tasks)
                        for n, res in zip(timeout_nodes, fallback_results):
                            wave_results_map[n.id] = res

                    wave_results = [wave_results_map.get(n.id, ToolResult(success=False, error="DCN Failure")) for n in nodes_to_run]
                else:
                    # Explicit Local Execution
                    wave_results = await asyncio.gather(*tasks)
            except Exception as e:
                logger.error(f"🛡️ [Resilience] DCN Error: {e}. Falling back to MONOLITH MODE.")
                # EMERGENCY LOCAL FALLBACK
                wave_results = await asyncio.gather(*tasks)


            
            # 3. Update State
            for n, res in zip(nodes_to_run, wave_results):
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
                pulse = dcn.sign_pulse(mission_id, json.dumps({k: v.message for k, v in results.items()}))
                asyncio.create_task(dcn.broadcast_gossip(pulse))

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
        memory_scope = "session"
        if node.contract:
            memory_scope = node.contract.memory_scope
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
                    await asyncio.sleep(compute_backoff_delay(attempts, retry_strategy))
        finally:
            AgentSandbox.deactivate(sandbox_token)

        # 6. Fallback mechanism
        if getattr(node, 'fallback_node_id', None):
             logger.info(f"[V8 Executor] Node {node.id} exhausted retries. Activating fallback: {node.fallback_node_id}")
             # In a real implementation, we might mark this node as 'failed_handled'
             # and the executor would then pick up the fallback node.
             # For now, we return a failure result indicating fallback is needed.

        compensation = self._run_compensation(node, mission_id=mission_id, agent_name=agent_name, error=last_error, mission_sm=mission_sm)
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

    def _run_compensation(
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
        compensation = {
            "action": action,
            "status": "executed",
            "error": error,
        }
        if mission_sm:
            mission_sm.record_node(node.id, "compensated", {"agent": agent_name, **compensation})
        logger.warning(
            "executor_compensation_executed",
            extra={
                "trace_id": mission_id,
                "mission_id": mission_id,
                "node_id": getattr(node, "id", None),
                "agent": agent_name,
                "status": "compensated",
                "duration_ms": 0,
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
