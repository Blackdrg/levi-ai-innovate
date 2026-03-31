"""
backend/services/orchestrator/executor.py

Execution engine for LEVI-AI plans.
Updated to interface with the new class-based hardened tool system.
"""

import logging
import asyncio
from typing import Dict, Any, List
from .orchestrator_types import ExecutionPlan, PlanStep, ToolResult
from .tool_registry import call_tool
from backend.utils.network import ai_service_breaker

logger = logging.getLogger(__name__)

async def _execute_step_with_resilience(
    step: PlanStep, 
    context: Dict[str, Any]
) -> ToolResult:
    """
    Executes a single plan step using the hardened tool system.
    Resilience (retries/timeouts) is handled at the tool level, 
    but we add an extra layer of circuit breaking here for network-level stability.
    """
    agent_name = step.agent
    start_time = asyncio.get_event_loop().time()
    
    # Merge global context with step-specific tool inputs
    # Phase 7: Dynamic Result Injection
    # Resolve placeholders like {{last_result}} in tool_input
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
    
    from backend.redis_client import HAS_REDIS, r as redis_client
    
    try:
        # Wrap Tool.execute() with a service-level circuit breaker
        raw_result = await ai_service_breaker.async_call(
            call_tool, agent_name, merged_params, context
        )
        
        # Ensure result is cast to ToolResult for consistency in the response
        if isinstance(raw_result, ToolResult):
            result = raw_result
        else:
            result = ToolResult(**raw_result)
        
        latency = int((asyncio.get_event_loop().time() - start_time) * 1000)
        result.latency_ms = latency
        
        # ── LEVI v6: Metric Tracking (The Reflex Ledger) ──
        if HAS_REDIS:
            tier = context.get("user_tier", "free")
            ledger_key = f"ledger:agent:{agent_name}"
            # Global & Tier-specific metrics
            redis_client.hincrby(ledger_key, "total_calls", 1)
            redis_client.hincrby(f"{ledger_key}:{tier}", "total_calls", 1)
            
            if result.success:
                redis_client.hincrby(ledger_key, "success_calls", 1)
                redis_client.hincrby(f"{ledger_key}:{tier}", "success_calls", 1)
                # Average latency (simplified moving average)
                prev_avg = float(redis_client.hget(ledger_key, "avg_latency_ms") or 0.0)
                new_avg = (prev_avg * 0.95) + (latency * 0.05) # Slower decay for v6 stabilization
                redis_client.hset(ledger_key, "avg_latency_ms", str(new_avg))
            else:
                redis_client.hincrby(ledger_key, "failure_calls", 1)
                redis_client.hincrby(f"{ledger_key}:{tier}", "failure_calls", 1)
                # Log error patterns for Meta-Brain pattern analysis (Phase 2 Shared Learning)
                error_snippet = (result.error or "Unknown").split(":")[0][:30]
                redis_client.hincrby(f"{ledger_key}:patterns", error_snippet, 1)

        # ── Fallback Logic ──────────────────────────────────────────────────
        if not result.success and step.fallback_agent:
            logger.warning(f"Step '{step.description}' failed. Attempting fallback to {step.fallback_agent}.")
            fb_raw = await call_tool(step.fallback_agent, merged_params, context)
            result = ToolResult(**fb_raw) if not isinstance(fb_raw, ToolResult) else fb_raw
            result.message = f"[FALLBACK] {result.message}"
            
        return result

    except Exception as e:
        logger.exception(f"Fatal execution error in step '{step.description}': {e}")
        return ToolResult(
            success=False,
            error=f"Execution engine failure: {str(e)}",
            agent=agent_name,
            retryable=False
        )

async def execute_plan(plan: ExecutionPlan, context: Dict[str, Any]) -> List[ToolResult]:
    """
    Sequentially executes an ExecutionPlan.
    Enforces 'critical' step logic to halt flows on unrecoverable errors.
    """
    results: List[ToolResult] = []
    
    logger.info(f"Executing Plan: {plan.intent} ({len(plan.steps)} steps)")
    
    for step in plan.steps:
        # Phase 8: Status Reporting
        status_cb = context.get("status_callback")
        if status_cb:
            msg = f"Executing {step.description}..."
            if asyncio.iscoroutinefunction(status_cb):
                await status_cb(msg)
            else:
                status_cb(msg)

        # Provide previous results to the current tool for multi-step reasoning
        context["execution_history"] = results
        # Convenience shortcut for the very last result
        context["last_result"] = results[-1].dict() if results else {}
        
        result = await _execute_step_with_resilience(step, context)
        
        # ── LEVI v6: Self-Correction Logic (v6 Reflection Loop) ──
        # Only run critique for reasoning/creative tasks (chat_agent/code_agent)
        # We trigger reflection if complexity is high AND result was successful but might need polish.
        if result.success and step.agent in ("chat_agent", "code_agent") and context.get("complexity", 0) >= 5:
            # Avoid infinite loops / max reflection depth = 1 in this sequential executor
            if "critique" not in context:
                logger.info(f"[Executor] Invoking v6 Validator for {step.agent}")
                
                # Call Validator (critic_agent)
                v_raw = await call_tool("critic_agent", {
                    "goal": context.get("input", ""),
                    "agent_output": result.message
                }, context)
                
                v_res = ToolResult(**v_raw) if not isinstance(v_raw, ToolResult) else v_raw
                
                if not v_res.success:
                    # Score was below threshold
                    score = v_res.data.get("quality_score", 0.0)
                    critique = v_res.data.get("critique", "Output lacks LEVI resonance.")
                    
                    logger.warning(f"[Executor] Self-Correction Triggered (Score: {score}). Critique: {critique[:60]}...")
                    
                    # One-time retry with critique context injected
                    context["critique"] = critique
                    result = await _execute_step_with_resilience(step, context)
                    # Remove critique for next steps
                    context.pop("critique")

        results.append(result)
        
        # Critical Step Enforcement: Halt if a mandatory component fails
        if not result.success and step.critical:
            logger.error(f"Critical step '{step.description}' failed. Halting plan execution.")
            break
            
    return results
