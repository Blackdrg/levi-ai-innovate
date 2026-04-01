"""
backend/core/executor.py

Execution engine for LEVI-AI v7 "Sovereign Mind".
Optimized for Parallel Pulse execution, mid-plan reflection, and failover resilience.
"""

import logging
import asyncio
import json
from typing import Dict, Any, List
from .orchestrator_types import ExecutionPlan, PlanStep, ToolResult
from .tool_registry import call_tool
from backend.utils.network import ai_service_breaker

logger = logging.getLogger(__name__)

async def _execute_step_with_resilience(step: PlanStep, context: Dict[str, Any]) -> ToolResult:
    """Executes a single plan step with dynamic injection and circuit breaking."""
    agent_name = step.agent
    start_time = asyncio.get_event_loop().time()
    
    # Resolve placeholders like {{last_result}}
    injected_inputs = {}
    for key, value in step.tool_input.items():
        if isinstance(value, str):
            if "{{last_result}}" in value:
                last_msg = context.get("last_result", {}).get("message", "")
                value = value.replace("{{last_result}}", last_msg)
            if "{{last_data}}" in value:
                last_data = str(context.get("last_result", {}).get("data", {}))
                value = value.replace("{{last_data}}", last_data)
        injected_inputs[key] = value

    merged_params = {**context, **injected_inputs}
    
    try:
        raw_result = await ai_service_breaker.async_call(call_tool, agent_name, merged_params, context)
        result = ToolResult(**raw_result) if not isinstance(raw_result, ToolResult) else raw_result
        result.latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        return result
    except Exception as e:
        logger.exception(f"Execution error in {agent_name}: {e}")
        return ToolResult(success=False, error=str(e), agent=agent_name)

async def _handle_agent_failover(step: PlanStep, failed_result: ToolResult, context: Dict[str, Any]) -> ToolResult:
    """Sovereign Resilience safety path fallback."""
    safety_map = {"research_agent": "search_agent", "document_agent": "chat_agent", "task_agent": "chat_agent"}
    fallback = safety_map.get(step.agent)
    if not fallback or fallback == step.agent: return failed_result
    
    logger.info(f"[Failover] Re-routing {step.agent} -> {fallback}")
    step.agent = fallback
    step.description = f"[RECOVERY] {step.description}"
    return await _execute_step_with_resilience(step, context)

async def _perform_agent_reflection(step: PlanStep, result: ToolResult, context: Dict[str, Any]) -> ToolResult:
    """Mid-plan self-critique loop to enhance reasoning quality."""
    max_turns = 1 if context.get("complexity_level", 0) < 3 else 2
    for turn in range(max_turns):
        v_raw = await call_tool("critic_agent", {"goal": context.get("input", step.description), "agent_output": result.message}, context)
        v_res = ToolResult(**v_raw) if not isinstance(v_raw, ToolResult) else v_raw
        if v_res.success and v_res.data.get("quality_score", 1.0) >= 0.85: break
        context["critique"] = v_res.data.get("critique", "Enhance precision.")
        result = await _execute_step_with_resilience(step, context)
    context.pop("critique", None)
    return result

async def execute_plan(plan: ExecutionPlan, context: Dict[str, Any]) -> List[ToolResult]:
    """Main execution orchestrator with Parallel Pulse detection."""
    results: List[ToolResult] = []
    logger.info(f"[Executor] v6.8.8 Pulse Starting: {plan.intent}")

    # 1. Sovereign Shield PII Protection
    if plan.is_sensitive:
        for step in plan.steps:
            step.agent = "local_agent"
            step.description = f"[SHIELDED] {step.description}"

    # 2. Parallel Grouping Logic
    step_groups = []
    current_group = []
    for step in plan.steps:
        step_json = json.dumps(step.tool_input)
        is_dependent = "{{last_result}}" in step_json or "{{last_data}}" in step_json
        if is_dependent and current_group:
            step_groups.append(current_group)
            current_group = [step]
        elif is_dependent:
            step_groups.append([step])
        else:
            current_group.append(step)
    if current_group: step_groups.append(current_group)

    # 3. Process Execution Groups
    for group in step_groups:
        if len(group) == 1:
            step = group[0]
            context["last_result"] = results[-1].dict() if results else {}
            result = await _execute_step_with_resilience(step, context)
            if result.success and step.agent in ("chat_agent", "search_agent", "research_agent") and context.get("complexity_level", 0) >= 2:
                result = await _perform_agent_reflection(step, result, context)
            if not result.success: result = await _handle_agent_failover(step, result, context)
            results.append(result)
            if not result.success and step.critical: break
        else:
            tasks = [_execute_step_with_resilience(s, {**context, "last_result": results[-1].dict() if results else {}}) for s in group]
            group_results = await asyncio.gather(*tasks)
            for idx, res in enumerate(group_results):
                if not res.success: res = await _handle_agent_failover(group[idx], res, context)
                results.append(res)
            best_res = sorted([r for r in group_results if r.success], key=lambda x: x.cost_score, reverse=True)
            if best_res: context["last_result"] = best_res[0].dict()
            if not any(r.success for r in group_results) and any(s.critical for s in group): break

    # 4. Final Instrumentation
    from backend.services.learning.logic import collect_interaction_log
    asyncio.create_task(collect_interaction_log(
        query=context.get("input", "unknown"),
        route=plan.intent,
        latency_ms=sum(r.latency_ms for r in results),
        success=results[-1].success if results else False,
        user_id=context.get("user_id"),
        agent_results=[r.dict() for r in results]
    ))

    return results
