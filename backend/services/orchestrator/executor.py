import logging
import asyncio
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .agent_registry import call_agent
from backend.utils.network import ai_service_breaker

logger = logging.getLogger(__name__)

class AgentExecutionError(Exception):
    """Specific error for agent failures to trigger retries."""
    pass

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(AgentExecutionError),
    reraise=True
)
async def _call_agent_with_retry(agent_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper to call an agent with standardized retry and circuit breaking."""
    try:
        result = await ai_service_breaker.async_call(call_agent, agent_name, context)
        
        if result.get("status") == "error" and result.get("retryable", True):
            raise AgentExecutionError(f"Agent {agent_name} failed: {result.get('error')}")
        
        return result
    except RuntimeError as re:
        # Circuit is OPEN
        logger.error(f"Circuit Breaker blocked call to {agent_name}: {re}")
        return {"status": "error", "error": "Circuit Breaker OPEN", "retryable": False}

async def execute_plan(plan: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute the generated plan sequentially with fallbacks."""
    results = []
    
    for step_info in plan:
        step_name = step_info.get("step", "unnamed_step")
        agent_name = step_info.get("agent", "chat_agent")
        
        logger.info(f"Executing step: {step_name} (Agent: {agent_name})")
        
        try:
            # 1. Primary Execution
            result = await _call_agent_with_retry(agent_name, context)
            
            # 2. Handle Explicit Errors
            if result.get("status") == "error":
                logger.warning(f"Step '{step_name}' failed. Falling back to chat.")
                result = await call_agent("chat_agent", context)
                result["fallback"] = True
                
            results.append({
                "step": step_name,
                "agent": agent_name,
                "result": result
            })
            
            # Update context for next steps
            context["last_result"] = result
            if "intermediate_results" not in context:
                context["intermediate_results"] = []
            context["intermediate_results"].append(result)
            
        except Exception as e:
            logger.error(f"Critical execution failure in {step_name}: {e}")
            # Final Fallback to Chat Agent
            fallback_result = await call_agent("chat_agent", context)
            results.append({
                "step": step_name,
                "agent": "chat_agent",
                "result": fallback_result,
                "error": f"Critical Failure: {str(e)}",
                "fallback": True
            })
            break # Stop execution on critical failure
            
    return results
