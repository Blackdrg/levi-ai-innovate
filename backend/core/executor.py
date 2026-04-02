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
from ..utils.network import ai_service_breaker

logger = logging.getLogger(__name__)

class GraphExecutor:
    """
    LeviBrain v8: Graph-Aware Executor.
    Processes task nodes based on topological dependencies.
    """

    async def execute(self, graph: Any, perception: Dict[str, Any]) -> List[ToolResult]:
        logger.info("[V8 Executor] Executing Task Graph...")
        results: Dict[str, ToolResult] = {}
        completed_ids: Set[str] = set()
        
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
            tasks = [self._execute_node(n, results, perception) for n in executable_nodes]
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

    async def _execute_node(self, node: Any, previous_results: Dict[str, ToolResult], perception: Dict[str, Any]) -> ToolResult:
        """Executes a single node with template-resolved inputs."""
        agent_name = node.agent
        start_time = asyncio.get_event_loop().time()
        
        # 1. Input Resolution ({{task_id.result}})
        resolved_inputs = self._resolve_inputs(node.inputs, previous_results)
        
        # 2. Parameter Synthesis
        merged_params = {
            **perception.get("context", {}), 
            **resolved_inputs, 
            "input": perception.get("input")
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
            logger.exception("[V8 Executor] Execution failed for %s: %s", agent_name, e)
            return ToolResult(success=False, error=str(e), agent=agent_name)

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
