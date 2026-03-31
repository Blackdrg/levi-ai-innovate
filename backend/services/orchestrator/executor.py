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
        # Cost score is already set in agent_registry.call_agent / tool_registry.call_tool (if updated)
        
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
        
        # 1. 🚀 Primary Execution
        result = await _execute_step_with_resilience(step, context)
        
        # 2. ── LEVI v6: Sovereign Agent Loop (Observe -> Critique -> Improve) ──
        # We trigger the autonomy loop for all reasoning-capable agents.
        REASONING_AGENTS = ("chat_agent", "code_agent", "search_agent", "diagnostic_agent")
        
        if result.success and step.agent in REASONING_AGENTS and context.get("complexity_level", 0) >= 1:
            # Max reflection turns based on task complexity
            max_reflection_turns = 1 if context.get("complexity_level", 0) < 3 else 2
            current_turn = 0
            
            while current_turn < max_reflection_turns:
                logger.info(f"[AgentLoop] Turn {current_turn+1} Reflection for {step.agent}")
                
                # A. 🔍 Observe & Critique (critic_agent)
                v_raw = await call_tool("critic_agent", {
                    "goal": context.get("input", step.description),
                    "agent_output": result.message,
                    "complexity": context.get("complexity_level", 2)
                }, context)
                
                v_res = ToolResult(**v_raw) if not isinstance(v_raw, ToolResult) else v_raw
                
                # B. Evaluation Logic
                quality_score = v_res.data.get("quality_score", 1.0)
                pass_threshold = 0.85 if context.get("complexity_level", 0) == 3 else 0.75
                
                if v_res.success and quality_score >= pass_threshold:
                    logger.info(f"[AgentLoop] Quality Check Passed ({quality_score:.2f})")
                    break
                
                # C. 💡 Self-Correction
                critique = v_res.data.get("critique", "Enhance precision and depth.")
                logger.warning(f"[AgentLoop] Quality Check Failed ({quality_score:.2f}). Critique: {critique[:100]}...")
                
                # Inject critique into context for the next attempt
                context["critique"] = critique
                context["reflection_count"] = current_turn + 1
                
                # D. Re-Execute with Correction
                result = await _execute_step_with_resilience(step, context)
                current_turn += 1
                
                # E. 📈 Learning Signal (Shared Intelligence)
                if result.success:
                    from backend.learning import collect_training_sample
                    asyncio.create_task(collect_training_sample(
                        user_message=f"CRITIQUE: {critique}\nORIGINAL_INPUT: {context.get('input', '')}",
                        bot_response=result.message,
                        mood=context.get("mood", "philosophical"),
                        rating=5, 
                        session_id=context.get("session_id", "reflect_loop"),
                        user_id=context.get("user_id")
                    ))

            # Cleanup reflection context
            context.pop("critique", None)
            context.pop("reflection_count", None)

        results.append(result)
        
        # 3. ── Critical Step Enforcement ──
        if not result.success and step.critical:
            logger.error(f"Critical step '{step.description}' failed. Halting plan execution.")
            break
            
    # ── 4. Final Instrumentation ──
    from backend.redis_client import HAS_REDIS
    if HAS_REDIS and results:
        from backend.redis_client import r as redis_client
        total_latency = sum(r.latency_ms for r in results)
        try:
            prev_lt = float(redis_client.get("stats:avg_latency_ms") or 0.0)
            new_lt = (prev_lt * 0.9) + (total_latency * 0.1)
            redis_client.set("stats:avg_latency_ms", str(new_lt))
        except: pass
        
    return results
