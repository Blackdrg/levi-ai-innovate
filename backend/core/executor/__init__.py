"""
Sovereign Execution Engine v8.
Executes the Task Graph (DAG) for cognitive missions.
Handles parallelization, dependency resolution, and agent coordination.
"""

import logging
import asyncio
import json
import os
from typing import Dict, Any, List, Set, Coroutine, Optional
from ..orchestrator_types import ToolResult, IntentResult
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

    async def execute(self, graph: Any, perception: Dict[str, Any], user_id: str = "global", policy: Optional[Any] = None) -> List[ToolResult]:


        logger.info("[V13.1 Executor] Executing Task Graph...")
        results: Dict[str, ToolResult] = {}
        completed_ids: Set[str] = set()
        
        mission_id = perception.get("request_id") or "global"
        blackboard = MissionBlackboard(mission_id)
        
        remaining_nodes = list(graph.nodes)
        wave_count = 0
        total_nodes_executed = 0
        tool_calls = 0
        mission_sm = CentralExecutionState(mission_id)

        
        while remaining_nodes:
            # 1. Mission Cancellation Check
            from backend.utils.mission import MissionControl
            mission_id = perception.get("request_id") or "global"
            if MissionControl.is_cancelled(mission_id):
                logger.warning(f"[V8 Executor] Mission {mission_id} cancelled by user. Aborting...")
                break

            # 2. Identify executable nodes (all deps satisfied)
            executable_nodes = [
                n for n in remaining_nodes 
                if all(dep in completed_ids for dep in n.dependencies)
            ]
            
            if not executable_nodes:
                if remaining_nodes:
                    logger.error("[V8 Executor] Dependency deadlock in graph.")
                break
            
            # Audit Point 07: Execution Guards
            wave_count += 1
            if wave_count > self.MAX_WAVES:
                logger.error(f"[Shield] Mission {mission_id} aborted: Wave limit ({self.MAX_WAVES}) exceeded.")
                SovereignBroadcaster.publish("MISSION_ABORTED", {"reason": "wave_limit_exceeded"}, user_id=user_id)
                break

            logger.debug("[V13.1 Executor] Executing Wave %d: %s", wave_count, [n.id for n in executable_nodes])
            
            # 2. Parallel Execution of Wave (Limited by Policy)
            max_parallel = policy.parallel_waves if policy else len(executable_nodes)
            try:
                if HAS_REDIS:
                    pressure = await redis_client.get("vram:pressure")
                    if pressure and str(pressure).lower() == "true":
                        max_parallel = max(1, min(max_parallel, 1))
            except Exception:
                pass
            nodes_to_run = executable_nodes[:max_parallel]
            
            total_nodes_executed += len(nodes_to_run)
            
            if total_nodes_executed >= self.WARNING_THRESHOLD and total_nodes_executed < self.MAX_MISSION_NODES:
                logger.warning(f"[V13.1 Executor] Mission {mission_id} reaching complexity threshold ({total_nodes_executed} nodes).")
                SovereignBroadcaster.publish("MISSION_WARNING", {"nodes_count": total_nodes_executed, "message": "High complexity mission detected. Approaching safety limit."}, user_id=user_id)

            if total_nodes_executed > self.MAX_MISSION_NODES:
                logger.error(f"[Shield] Mission {mission_id} aborted: Node limit ({self.MAX_MISSION_NODES}) exceeded.")
                SovereignBroadcaster.publish("MISSION_ABORTED", {"reason": "node_limit_exceeded"}, user_id=user_id)
                break

            tasks = [self._execute_node(n, results, perception, blackboard=blackboard, user_id=user_id, wave_count=wave_count, policy=policy, mission_sm=mission_sm) for n in nodes_to_run]
            SovereignBroadcaster.publish("WAVE_STARTED", {"nodes": [n.id for n in nodes_to_run], "current_wave": wave_count}, user_id=user_id)

            # --- Distributed Wave Management (v2.0-Hardened) ---
            try:
                if os.getenv("DISTRIBUTED_MODE", "false").lower() == "true" and HAS_REDIS:
                    from .distributed import DistributedGraphExecutor
                    dist_executor = DistributedGraphExecutor(redis_client)
                    
                    # 1. Enqueue Wave
                    previous_results_serializable = {k: v.dict() for k, v in results.items()}
                    await dist_executor.enqueue_wave(mission_id, executable_nodes, perception, previous_results_serializable)
                    
                    # 2. Reactive Result Management (v2.1-Hardened)
                    pubsub = redis_client.pubsub()
                    event_channel = f"dcn:mission:{mission_id}:events"
                    await pubsub.subscribe(event_channel)
                    
                    pending_node_ids = set(n.id for n in executable_nodes)
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
                        timeout_nodes = [n for n in executable_nodes if n.id in pending_node_ids]
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
                tool_calls += 1
                if policy and getattr(policy, "budget", None) and tool_calls >= policy.budget.tool_call_limit:
                    logger.error(f"[Shield] Mission {mission_id} aborted: Tool call limit ({policy.budget.tool_call_limit}) reached.")
                    break
                
            # 4. Critical Path Failure Check
            critical_failure = False
            for n in nodes_to_run:
                res = results[n.id]
                if not res.success and n.critical:
                    critical_failure = True
                    logger.warning("[V8 Executor] Critical task failure: %s", n.id)
                    break
            
            if critical_failure:
                break
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

        attempts = 0
        last_error = None
        
        # Timeline recorder: node start
        try:
            CognitiveTracer.add_step(perception.get("request_id", "global"), "node_start", {"node_id": node.id, "agent": agent_name})
        except Exception:
            pass

        while attempts <= max_retries:
            try:
                attempts += 1
                
                # 2.5 Rate Limit Check (v9.8.1 Protection)
                if not await check_agent_limit(user_id, agent_name, limit=60): # 60/hr/agent default
                    return ToolResult(
                        success=False, 
                        error=f"Sovereign Rate Limit Exceeded for agent '{agent_name}'. Please wait before next mission.", 
                        agent=agent_name
                    )

                # 3. Check for Swarm Consensus Requirements (v9.8.1)
                # Trigged if node is 'fragile', 'high_friction', or 'consensus' is explicitly requested
                is_fragile = getattr(node, 'is_fragile', False) or getattr(node, 'high_friction', False)
                
                if is_fragile and attempts == 1:
                    logger.info(f"[V8 Swarm] Mission Fragility Detected for node {node.id}. Activating Consensus Adjudication.")
                    
                    # Parallel Swarm Run: Execute multiple perspectives
                    # We run the primary agent vs a 'Corrective' profile (Critic) and an 'Optimized' profile
                    swarm_tasks = [
                        ai_service_breaker.async_call(call_tool, agent_name, merged_params, perception.get("context", {})), # Primary
                        ai_service_breaker.async_call(call_tool, "Critic", merged_params, perception.get("context", {})),  # Critic
                        ai_service_breaker.async_call(call_tool, "Optimizer", merged_params, perception.get("context", {})) # Optimizer
                    ]
                    
                    candidate_results = await asyncio.gather(*swarm_tasks, return_exceptions=True)
                    valid_candidates = []
                    
                    for cr in candidate_results:
                        if isinstance(cr, Exception): continue
                        if isinstance(cr, dict): valid_candidates.append(AgentResult(**cr) if "success" in cr else AgentResult(success=True, message=str(cr), agent="unknown"))
                        elif isinstance(cr, ToolResult): valid_candidates.append(cr)
                        else: valid_candidates.append(cr) # Assume it's a result object
                    
                    # 4. Consensus Adjudication (v13.1)
                    consensus_agent = ConsensusAgentV11()
                    from ...agents.consensus_agent import ConsensusInput, FidelityRubric
                    
                    # Synthesize rubrics from candidates if available
                    candidate_rubrics = [
                        FidelityRubric(
                            syntax_correctness=getattr(c, 'syntax_score', 0.9),
                            logical_consistency=getattr(c, 'logic_score', 0.8),
                            factual_grounding=getattr(c, 'grounding_score', 0.85),
                            sovereign_resonance=getattr(c, 'resonance_score', 0.9)
                        ) for c in valid_candidates
                    ]

                    consensus_res = await consensus_agent.execute(ConsensusInput(
                        goal=perception.get("input", "Synchronous mission"),
                        candidates=valid_candidates,
                        rubrics=candidate_rubrics,
                        context=perception.get("context", {})
                    ))
                    
                    if consensus_res.success:
                        # Extract the winning candidate from the consensus data
                        winner_data = consensus_res.data.get("winner", {})
                        result = ToolResult(
                            success=True, 
                            message=winner_data.get("message", "Consensus selected winner."),
                            agent=winner_data.get("agent", agent_name),
                            data=winner_data.get("data", {}),
                            fidelity_score=consensus_res.fidelity_score
                        )
                    else:
                        # Fallback to the first valid candidate if consensus fails
                        result = valid_candidates[0] if valid_candidates else ToolResult(success=False, error="Swarm failure", agent=agent_name)
                
                # Standard Single-Agent Execution
                # 1. Determine Timeout (Contract > Budget > Default)
                timeout = 15
                if node.contract and node.contract.timeout_ms:
                    timeout = node.contract.timeout_ms / 1000.0
                elif policy and getattr(policy, "budget", None):
                    timeout = policy.budget.cpu_time_limit_ms / 1000.0

                # 2. Check Allowed Tools (Contract Enforcement)
                if node.contract and node.contract.allowed_tools:
                    # Logic to restrict agent tool usage if the agent supports dynamic tool binding
                    pass

                # 3. Worker Isolation: memory_scope & sandbox
                memory_scope = "session"
                if node.contract:
                    memory_scope = node.contract.memory_scope
                
                # Bounded execution quota check (token_limit, tool_call_limit)
                if policy and policy.budget:
                    if tool_calls >= policy.budget.tool_call_limit:
                         return ToolResult(success=False, error="Tool call limit exceeded", agent=agent_name)
                    # Note: token_limit is usually checked post-execution or via agent-level callbacks
                
                logger.debug(f"[TEC] Executing {node.id} with timeout={timeout}s, scope={memory_scope}")
                
                # Standard Single-Agent Execution
                raw_res = await asyncio.wait_for(
                    ai_service_breaker.async_call(
                        call_tool, 
                        agent_name, 
                        {**merged_params, "__memory_scope__": memory_scope, "__sandbox__": policy.sandbox_required if policy else False}, 
                        {**perception.get("context", {}), "model_tier": getattr(node, "model_tier", "L2")}
                    ),
                    timeout=timeout
                )
                    
                    if not isinstance(raw_res, ToolResult):
                        result = ToolResult(**raw_res) if isinstance(raw_res, dict) else ToolResult(success=True, message=str(raw_res), agent=agent_name)
                    else:
                        result = raw_res
                
                # Success Check
                if result.success:
                    result.latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                    
                    # Audit Point 05: Output Sanitization
                    result.message = ResultSanitizer.sanitize_bot_response(result.message or "")
                    
                    # Audit Point 20: CU Billing / Usage Tracking
                    prompt_tokens = getattr(result, "prompt_tokens", 0)
                    completion_tokens = getattr(result, "completion_tokens", 0)
                    # Simplified CU calculation: 1.0 per task + tokens/1000
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
                                cu_cost=calculated_cu
                            )
                            session.add(usage)
                            await session.commit()
                    except Exception as e:
                        logger.error(f"[V13.1 Executor] Failed to log CU usage: {e}")

                    # 5. Blackboard Update
                    if isinstance(result.data, dict) and "blackboard_update" in result.data:
                        for k, v in result.data["blackboard_update"].items():
                            blackboard.add_artifact(k, v)
                    
                    if hasattr(result, "insight") and result.insight:
                        blackboard.update_insight(agent_name, result.insight)
                    
                    # Telemetry
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
                    
                    return result
                
                else:
                    last_error = result.error or "Unknown failure"
                    logger.warning(f"[V8 Executor] Agent {agent_name} failed (Attempt {attempts}/{max_retries+1}): {last_error}")

            except asyncio.TimeoutError:
                last_error = f"Timeout ({timeout}s)"
                logger.error(f"[V8 Executor] Agent {agent_name} timed out.")
            except Exception as e:
                last_error = str(e)
                logger.exception(f"[V8 Executor] Agent {agent_name} crashed: {e}")

            if attempts <= max_retries:
                # Optional: Exponential Backoff delay
                await asyncio.sleep(2 ** attempts)

        # 6. Fallback mechanism
        if getattr(node, 'fallback_node_id', None):
             logger.info(f"[V8 Executor] Node {node.id} exhausted retries. Activating fallback: {node.fallback_node_id}")
             # In a real implementation, we might mark this node as 'failed_handled'
             # and the executor would then pick up the fallback node.
             # For now, we return a failure result indicating fallback is needed.

        if mission_sm:
            mission_sm.record_node(node.id, "failed", {"agent": agent_name, "error": last_error})
        return ToolResult(success=False, error=f"Max retries exceeded: {last_error}", agent=agent_name)

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
