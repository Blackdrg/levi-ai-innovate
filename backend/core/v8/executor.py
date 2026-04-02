import logging
import asyncio
import json
from typing import Dict, Any, List, Set, Coroutine
from ..orchestrator_types import ToolResult, IntentResult
from ..tool_registry import call_tool
from ...utils.network import ai_service_breaker

logger = logging.getLogger(__name__)

class GraphExecutor:
    """
    LeviBrain v8: Graph-Aware Executor
    Executes DAG task nodes in parallel where possible.
    """

    async def run(self, graph: Any, perception: Dict[str, Any]) -> List[ToolResult]:
        logger.info("[V8 Executor] Executing Task Graph...")
        results: Dict[str, ToolResult] = {}
        completed_ids: Set[str] = set()
        
        # 1. Topological Sorting / Parallel Execution Grouping
        # For simplicity, we'll iterate in waves of independent tasks
        remaining_nodes = list(graph.nodes)
        
        while remaining_nodes:
            # Nodes with all dependencies met
            executable_nodes = [
                n for n in remaining_nodes 
                if all(dep in completed_ids for dep in n.dependencies)
            ]
            
            if not executable_nodes:
                # Circular dependency or missing task
                logger.error("[V8 Executor] Deadlock detected in graph.")
                break
            
            logger.debug("[V8 Executor] Wave Execution: %s", [n.id for n in executable_nodes])
            
            # Execute wave in parallel
            tasks = [self._execute_node(n, results, perception) for n in executable_nodes]
            wave_results = await asyncio.gather(*tasks)
            
            for n, res in zip(executable_nodes, wave_results):
                results[n.id] = res
                completed_ids.add(n.id)
                remaining_nodes.remove(n)
                
            # Early exit if a critical task fails
            if any(not res.success and next(n.critical for n in executable_nodes if n.id == res.agent_id) for res in wave_results):
                 logger.warning("[V8 Executor] Critical failure in wave. Stopping.")
                 break

        return list(results.values())

    async def _execute_node(self, node: Any, previous_results: Dict[str, ToolResult], perception: Dict[str, Any]) -> ToolResult:
        """Executes a single task node with dynamic input resolution."""
        agent_name = node.agent
        start_time = asyncio.get_event_loop().time()
        
        # Resolve placeholders like {{task_id.result}}
        resolved_inputs = self._resolve_inputs(node.inputs, previous_results)
        
        # Merge with perception & context
        merged_params = {**perception.get("context", {}), **resolved_inputs, "input": perception.get("input")}
        
        try:
            raw_res = await ai_service_breaker.async_call(call_tool, agent_name, merged_params, perception["context"])
            result = ToolResult(**raw_res) if not isinstance(raw_res, ToolResult) else raw_res
            result.latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            # Add agent_id field to help Wave logic (ToolResult doesn't have it by default in v7)
            setattr(result, "agent_id", node.id)
            return result
        except Exception as e:
            logger.exception(f"Node execution error ({agent_name}): {e}")
            return ToolResult(success=False, error=str(e), agent=agent_name)

    def _resolve_inputs(self, inputs: Dict[str, Any], previous_results: Dict[str, ToolResult]) -> Dict[str, Any]:
        """Resolves template-style inputs from previous results."""
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, str) and "{{" in value and "}}" in value:
                # Format: {{task_id.result}} or {{task_id.data}}
                template = value.replace("{{", "").replace("}}", "")
                parts = template.split(".")
                task_id = parts[0]
                attr = parts[1] if len(parts) > 1 else "message" # Default to message
                
                if task_id in previous_results:
                    res = previous_results[task_id]
                    if attr == "result": resolved[key] = res.message
                    elif attr == "data": resolved[key] = str(res.data)
                    else: resolved[key] = str(getattr(res, attr, ""))
                else:
                    resolved[key] = value # Keep original if not found
            else:
                resolved[key] = value
        return resolved
