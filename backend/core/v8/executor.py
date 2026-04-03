import logging
import asyncio
import json
from typing import Dict, Any, List, Set, Coroutine
from ..orchestrator_types import ToolResult, IntentResult
from ..tool_registry import call_tool
from ...utils.network import ai_service_breaker

# V8.8 Bridge: Telemetry & Push Notifications
from backend.api.v8.telemetry import broadcast_mission_event
from backend.services.push_service import PushService
from backend.core.v8.blackboard import MissionBlackboard
from backend.core.v8.dreaming_task import DreamingTask

logger = logging.getLogger(__name__)

class GraphExecutor:
    """
    LeviBrain v8: Graph-Aware Executor
    Executes DAG task nodes in parallel where possible.
    """

    async def run(self, graph: Any, perception: Dict[str, Any]) -> List[ToolResult]:
        logger.info("[V8 Executor] Initiating Topological Wave Execution...")
        # 1. Start Telemetry & Blackboard
        user_id = perception.get("user_id", "default_user")
        session_id = perception.get("session_id", "default_session")
        
        broadcast_mission_event(user_id, "mission_start", {"graph_size": len(graph.nodes), "input": perception.get("input")})
        
        # Swarm Intelligence: Initialize & Clear Blackboard for the new mission
        blackboard = MissionBlackboard(session_id)
        await blackboard.clear()
        
        # 2. Dynamic DAG Execution Loop
        while not graph.is_complete():
            # Identify executable nodes via active graph state
            executable_nodes = graph.get_ready_tasks()
            
            if not executable_nodes:
                logger.error("[V8 Executor] Dependency deadlock in mission graph.")
                break
            
            logger.debug("[V8 Executor] Dispatching Wave: %s", [n.id for n in executable_nodes])
            
            # 3. Parallel Execution of Wave
            tasks = [self._execute_node(n, graph.results, perception) for n in executable_nodes]
            wave_results = await asyncio.gather(*tasks)
            
            # 4. State Synchronization & Telemetry
            for n, res in zip(executable_nodes, wave_results):
                graph.mark_complete(n.id, res)
                
                # Broadcast Task Completion
                broadcast_mission_event(user_id, "task_complete", {
                    "id": n.id, 
                    "success": res.success, 
                    "latency": res.latency_ms,
                    "agent": n.agent
                })
                
                # Critical Path Failure Check
                if not res.success and n.critical:
                    logger.warning("[V8 Executor] Critical mission failure at node: %s", n.id)
                    # 5. Push Notification for Critical Failure
                    push = PushService()
                    await push.send_critical_alert(
                        user_id=user_id,
                        title="Critical Mission Failure",
                        message=f"LEVI mission aborted: Node '{n.id}' failed.",
                        data={"node": n.id, "agent": n.agent}
                    )
                    broadcast_mission_event(user_id, "mission_aborted", {"reason": f"Critical failure: {n.id}"})
                    return list(graph.results.values())
        
        # 6. Final Telemetry & Evolutionary Intelligence
        if graph.is_complete():
            broadcast_mission_event(user_id, "mission_complete", {"status": "success"})
            
            # Post Final Mission Summary to Blackboard for session continuity
            summary = f"Mission successfully completed. {len(graph.results)} tasks crystallized."
            await blackboard.post_insight("executor", summary, tag="mission_summary")
            
            # Trigger 'Dreaming Phase' (Episodic -> Semantic)
            await DreamingTask.increment_and_check(user_id)

        return list(graph.results.values())

    async def _execute_node(self, node: Any, previous_results: Dict[str, ToolResult], perception: Dict[str, Any]) -> ToolResult:
        """Executes a single node with template-resolved inputs and circuit-breaker protection."""
        agent_name = node.agent
        start_time = asyncio.get_event_loop().time()
        
        # 1. Input Resolution ({{task_id.result}})
        resolved_inputs = self._resolve_inputs(node, node.inputs, previous_results)
        
        # 2. Swarm Context Injection (Blackboard)
        session_id = perception.get("session_id", "default_session")
        blackboard_context = await MissionBlackboard.get_session_context(session_id)
        
        # 3. Parameter Synthesis
        merged_params = {
            **perception.get("context", {}), 
            **resolved_inputs, 
            "input": perception.get("input"),
            "blackboard_context": blackboard_context,
            "session_id": session_id
        }
        
        try:
            # 3. Secure Invocation with Circuit Breaker
            raw_res = await ai_service_breaker.async_call(
                call_tool, 
                agent_name, 
                merged_params, 
                perception.get("context", {})
            )
            
            # 4. Result Normalization
            if not isinstance(raw_res, ToolResult):
                 result = ToolResult(**raw_res) if isinstance(raw_res, dict) else ToolResult(success=True, message=str(raw_res), agent=agent_name)
            else:
                 result = raw_res
                 
            result.latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            return result
            
        except Exception as e:
            logger.exception("[V8 Executor] Wave execution failure for %s: %s", agent_name, e)
            return ToolResult(success=False, error=str(e), agent=agent_name)

    def _resolve_inputs(self, node: Any, inputs: Dict[str, Any], previous_results: Dict[str, ToolResult]) -> Dict[str, Any]:
        """Resolves template placeholders like {{task_search.result}} or {{all_results}}."""
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, str) and "{{" in value and "}}" in value:
                template = value.replace("{{", "").replace("}}", "")
                
                if template == "dependency_results":
                    # V8.7 Swarm Optimization: Returns a mapping of ONLY direct dependency results
                    resolved[key] = {tid: res.message for tid, res in previous_results.items() if tid in node.dependencies and res.success}
                    continue
                    
                if template == "all_results":
                    # Legacy v8.5: Returns a mapping of all successful results
                    resolved[key] = {tid: res.message for tid, res in previous_results.items() if res.success}
                    continue
                
                parts = template.split(".")
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
