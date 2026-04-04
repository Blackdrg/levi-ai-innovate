"""
Sovereign Execution Engine v8.
Executes the Task Graph (DAG) for cognitive missions.
Handles parallelization, dependency resolution, and agent coordination.
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Set, Coroutine
from .orchestrator_types import ToolResult, IntentResult
from .tool_registry import call_tool
from backend.broadcast_utils import SovereignBroadcaster, PULSE_NODE_COMPLETED
from ..utils.network import ai_service_breaker
from ..celery_app import celery_app
from ..agents.registry import AGENT_REGISTRY
from ..agents.consensus_agent import ConsensusAgentV8
from ..utils.rate_limit import check_agent_limit


logger = logging.getLogger(__name__)

class GraphExecutor:
    """
    LeviBrain v8: Graph-Aware Executor.
    Processes task nodes based on topological dependencies.
    """

    async def execute(self, graph: Any, perception: Dict[str, Any], user_id: str = "global") -> List[ToolResult]:

        logger.info("[V8 Executor] Executing Task Graph...")
        results: Dict[str, ToolResult] = {}
        completed_ids: Set[str] = set()
        blackboard: Dict[str, Any] = {} # v8 Swarm Communication
        
        remaining_nodes = list(graph.nodes)

        
        while remaining_nodes:
            # 1. Identify executable nodes (all deps satisfied)
            executable_nodes = [
                n for n in remaining_nodes 
                if all(dep in completed_ids for dep in n.dependencies)
            ]
            
            if not executable_nodes:
                if remaining_nodes:
                    logger.error("[V8 Executor] Dependency deadlock in graph.")
                break
            
            logger.debug("[V8 Executor] Executing Wave: %s", [n.id for n in executable_nodes])
            
            # 2. Parallel Execution of Wave
            tasks = [self._execute_node(n, results, perception, blackboard=blackboard, user_id=user_id) for n in executable_nodes]
            SovereignBroadcaster.publish("WAVE_STARTED", {"nodes": [n.id for n in executable_nodes]}, user_id=user_id)

            wave_results = await asyncio.gather(*tasks)


            
            # 3. Update State
            for n, res in zip(executable_nodes, wave_results):
                results[n.id] = res
                completed_ids.add(n.id)
                remaining_nodes.remove(n)
                
            # 4. Critical Path Failure Check
            critical_failure = False
            for n in executable_nodes:
                res = results[n.id]
                if not res.success and n.critical:
                    critical_failure = True
                    logger.warning("[V8 Executor] Critical task failure: %s", n.id)
                    break
            
            if critical_failure:
                break

        return list(results.values())

    async def _execute_node(self, node: Any, previous_results: Dict[str, ToolResult], perception: Dict[str, Any], blackboard: Dict[str, Any] = None, user_id: str = "global") -> ToolResult:
        """Executes a single node with template-resolved inputs, retries and fallbacks."""
        agent_name = node.agent
        start_time = asyncio.get_event_loop().time()
        max_retries = getattr(node, 'retry_count', 2)
        timeout = getattr(node, 'timeout', 30) # Default 30s
        
        # 1. Input Resolution ({{task_id.result}})
        resolved_inputs = self._resolve_inputs(node.inputs, previous_results)
        
        # 2. Parameter Synthesis
        merged_params = {
            **perception.get("context", {}), 
            **resolved_inputs, 
            "input": perception.get("input"),
            "__blackboard__": blackboard or {} # Injected swarm state
        }

        attempts = 0
        last_error = None
        
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
                        ai_service_breaker.async_call(call_tool, "critic", merged_params, perception.get("context", {})),  # Critic
                        ai_service_breaker.async_call(call_tool, "optimizer", merged_params, perception.get("context", {})) # Optimizer
                    ]
                    
                    candidate_results = await asyncio.gather(*swarm_tasks, return_exceptions=True)
                    valid_candidates = []
                    
                    for cr in candidate_results:
                        if isinstance(cr, Exception): continue
                        if isinstance(cr, dict): valid_candidates.append(AgentResult(**cr) if "success" in cr else AgentResult(success=True, message=str(cr), agent="unknown"))
                        elif isinstance(cr, ToolResult): valid_candidates.append(cr)
                        else: valid_candidates.append(cr) # Assume it's a result object
                    
                    # 4. Consensus Adjudication
                    consensus_agent = ConsensusAgentV8()
                    from ..agents.consensus_agent import ConsensusInput
                    consensus_res = await consensus_agent.execute(ConsensusInput(
                        goal=perception.get("input", "Synchronous mission"),
                        candidates=valid_candidates,
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
                
                else:
                    # Standard Single-Agent Execution
                    raw_res = await asyncio.wait_for(
                        ai_service_breaker.async_call(
                            call_tool, 
                            agent_name, 
                            merged_params, 
                            perception.get("context", {})
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
                    
                    # 5. Blackboard Update
                    if isinstance(result.data, dict) and "blackboard_update" in result.data:
                        blackboard.update(result.data["blackboard_update"])
                    
                    # Telemetry
                    SovereignBroadcaster.publish(PULSE_NODE_COMPLETED, {
                        "node_id": node.id, 
                        "agent": agent_name,
                        "success": True,
                        "latency": result.latency_ms,
                        "fidelity": getattr(result, 'fidelity_score', 0.0)
                    }, user_id=user_id)
                    
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
