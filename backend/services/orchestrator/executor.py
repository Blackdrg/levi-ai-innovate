import logging
from typing import List, Dict, Any
from .agent_registry import call_agent

logger = logging.getLogger(__name__)

async def execute_plan(plan: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute the generated plan sequentially, passing context between steps."""
    results = []
    
    for step_info in plan:
        step_name = step_info.get("step", "unnamed_step")
        agent_name = step_info.get("agent", "chat_agent")
        
        logger.info(f"Executing step: {step_name} with agent: {agent_name}")
        
        # Call the agent with the current context
        try:
            result = await call_agent(agent_name, context)
            
            # Store the result and update context for the next step
            results.append({
                "step": step_name,
                "agent": agent_name,
                "result": result
            })
            
            # Pass the latest results to the next agent
            context["last_result"] = result
            context["intermediate_results"] = results
            
            # Stop if there's a fatal error in a step
            if result.get("status") == "error":
                logger.error(f"Execution halted due to error in step {step_name}")
                break
                
        except Exception as e:
            logger.error(f"Exception during step execution {step_name}: {e}")
            results.append({
                "step": step_name,
                "agent": agent_name,
                "error": str(e)
            })
            break
            
    return results
