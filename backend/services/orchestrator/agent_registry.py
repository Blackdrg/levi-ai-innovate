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
    # This would typically trigger a background task or return instructions to the frontend
    prompt = context.get("last_result", {}).get("message", context.get("input", ""))
    mood = context.get("mood", "philosophical")
    
    return {
        "message": f"I am preparing to visualize this: '{prompt}'.",
        "action": "generate_image",
        "params": {"text": prompt, "mood": mood},
        "agent": "image_agent"
    }

@register_agent("research_agent")
async def research_handler(context: Dict[str, Any]) -> Dict[str, Any]:
    query = context.get("input", "")
    # Mocking search results for now
    return {
        "message": f"I've looked into '{query}'. AI trends are moving towards multi-modal orchestration (ironically).",
        "results": [{"title": "AI Trends 2026", "snippet": "Agents are everywhere."}],
        "agent": "research_agent"
    }
