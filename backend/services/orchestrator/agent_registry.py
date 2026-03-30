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
        return {
            "status": "error",
            "error": str(e),
            "agent": name,
            "retryable": True # Default to retryable for unexpected exceptions
        }

# --- Specialized Agents ---

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
    return {
        "message": response,
        "agent": "chat_agent",
        "status": "success",
        "retryable": False
    }

@register_agent("image_agent")
async def image_handler(context: Dict[str, Any]) -> Dict[str, Any]:
    """Connects the Orchestrator to the LEVI Studio (Image Gen)."""
    from backend.services.studio.utils import create_studio_job
    
    message = context.get("last_result", {}).get("message", context.get("input", ""))
    user_id = context.get("user_id", "guest")
    user_tier = context.get("user_tier", "free")
    mood = context.get("mood", "philosophical")
    
    result = create_studio_job(
        task_type="image",
        params={"text": message, "mood": mood},
        user_id=user_id,
        user_tier=user_tier
    )
    
    if result.get("status") == "error":
        return {
            "status": "error",
            "message": result.get("error", "Studio failed."),
            "agent": "image_agent",
            "retryable": True
        }

    return {
        "message": f"I have visualized your concept: '{message}'. The masterpiece is being rendered.",
        "job_id": result.get("job_id"),
        "agent": "image_agent",
        "status": "success"
    }

@register_agent("search_agent")
async def search_handler(context: Dict[str, Any]) -> Dict[str, Any]:
    """Uses LLM to perform deep thematic research / search simulation."""
    from backend.generation import _async_call_llm_api
    from backend.payments import use_credits
    
    user_id = context.get("user_id", "guest")
    topic = context.get("input", "the unknown")
    
    # Phase 4: Credit Deduction (Search = 1 credit)
    if user_id and not user_id.startswith("guest:"):
        try:
            use_credits(str(user_id), 1)
        except Exception as ce:
            logger.warning(f"Credit deduction failed for search: {ce}")
            return {
                "status": "error",
                "message": "Search requires credits. Your balance is insufficient.",
                "agent": "search_agent",
                "retryable": False
            }

    system_prompt = (
        "You are the LEVI Search Engine. Provide 3-5 concise, deep, and factual insights "
        "about the user topic. Focus on historical context, scientific facts, or philosophical depth. "
        "Be precise and informative. Format as plain text with bullet points."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Search Topic: {topic}"}
    ]
    
    search_results = await _async_call_llm_api(
        messages=messages,
        model="llama-3.1-8b-instant",
        provider="groq"
    )
    
    return {
        "message": search_results or "The collective knowledge is silent on this matter.",
        "agent": "search_agent",
        "status": "success",
        "retryable": False
    }

@register_agent("code_agent")
async def code_handler(context: Dict[str, Any]) -> Dict[str, Any]:
    """Generates clean, functional code with architectural explanations."""
    from backend.generation import _async_call_llm_api
    from backend.payments import use_credits
    
    user_id = context.get("user_id", "guest")
    task = context.get("input", "")
    
    # Phase 4: Credit Deduction (Code = 2 credits)
    if user_id and not user_id.startswith("guest:"):
        try:
            use_credits(str(user_id), 2)
        except Exception as ce:
            logger.warning(f"Credit deduction failed for code: {ce}")
            return {
                "status": "error",
                "message": "Architectural logic requires 2 credits. Your balance is insufficient.",
                "agent": "code_agent",
                "retryable": False
            }

    system_prompt = (
        "You are the LEVI Architect. Generate clean, efficient, and well-documented code "
        "for the user's request. Include a brief architectural explanation of WHY you chose "
        "this approach. Use the requested language or Python by default."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Code Task: {task}"}
    ]
    
    code_output = await _async_call_llm_api(
        messages=messages,
        model="llama-3.1-70b-versatile", # Code requires more intelligence
        provider="groq"
    )
    
    return {
        "message": code_output or "I could not construct the logic you requested.",
        "agent": "code_agent",
        "status": "success",
        "retryable": False
    }

