from typing import Dict, Any, Callable, Awaitable
import logging

logger = logging.getLogger(__name__)

# Type definition for local handlers
AgentHandler = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]

AGENTS: Dict[str, AgentHandler] = {}

def register_agent(name: str):
    def decorator(func: AgentHandler):
        AGENTS[name] = func
        return func
    return decorator

async def call_agent(name: str, context: Dict[str, Any]) -> Dict[str, Any]:
    if name not in AGENTS:
        logger.error(f"Agent {name} not found in registry.")
        return {"error": f"Agent {name} not found"}
    
    logger.info(f"Calling agent: {name}")
    try:
        return await AGENTS[name](context)
    except Exception as e:
        logger.exception(f"Error executing agent {name}: {e}")
        return {"error": str(e)}

# --- Placeholder Agents ---

@register_agent("chat_agent")
async def chat_handler(context: Dict[str, Any]) -> Dict[str, Any]:
    from backend.generation import generate_response
    
    prompt = context.get("input", "")
    history = context.get("history", [])
    mood = context.get("mood", "philosophical")
    user_tier = context.get("user_tier", "free")
    
    response = await generate_response(
        prompt=prompt,
        history=history,
        mood=mood,
        user_tier=user_tier
    )
    return {"message": response, "agent": "chat_agent"}

@register_agent("image_agent")
async def image_handler(context: Dict[str, Any]) -> Dict[str, Any]:
    """Connects the Orchestrator to the LEVI Studio (Image Gen)."""
    from backend.services.studio.utils import create_studio_job
    
    # Extract the refined prompt from previous steps or the original input
    message = context.get("last_result", {}).get("message", context.get("input", ""))
    user_id = context.get("user_id", "guest")
    user_tier = context.get("user_tier", "free")
    mood = context.get("mood", "philosophical")
    
    # Trigger the architectural studio logic
    result = create_studio_job(
        task_type="image",
        params={"text": message, "mood": mood},
        user_id=user_id,
        user_tier=user_tier
    )
    
    if result.get("status") == "error":
        return {"status": "error", "message": result.get("error", "Studio failed.")}

    return {
        "message": f"I have visualized your concept: '{message}'. The masterpiece is being rendered (Job ID: {result.get('job_id')}).",
        "job_id": result.get("job_id"),
        "agent": "image_agent",
        "status": "success"
    }

@register_agent("research_agent")
async def research_handler(context: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates research by using the LLM to gather context on a topic."""
    from .planner import call_lightweight_llm
    
    topic = context.get("input", "general existence")
    
    system_prompt = (
        "You are the LEVI Researcher. Provide 3-4 concise, deep, and factual 'research notes' "
        "about the user topic. Focus on philosophical, historical, or scientific depth. "
        "Format as a list of facts."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Research Topic: {topic}"}
    ]
    
    research_notes = await call_lightweight_llm(messages)
    
    return {
        "message": research_notes or "Research indicates a profound void in this specific area.",
        "agent": "research_agent",
        "status": "success"
    }
