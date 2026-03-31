from typing import Dict, Any, Callable, Awaitable, Optional
import logging
import hashlib
import json

from .tool_contracts import ToolContract
from .orchestrator_types import ToolResult

logger = logging.getLogger(__name__)

# Type definition for local handlers
AgentHandler = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]

AGENTS: Dict[str, AgentHandler] = {}

def register_agent(name: str):
    def decorator(func: AgentHandler):
        AGENTS[name] = func
        return func
    return decorator

async def call_agent(name: str, context: Dict[str, Any]) -> ToolResult:
    if name not in AGENTS:
        logger.error(f"Agent {name} not found in registry.")
        return ToolContract.wrap_result(name, success=False, error=f"Agent {name} not found")
    
    logger.info(f"Calling agent: {name}")
    try:
        res = await AGENTS[name](context)
        if isinstance(res, ToolResult):
            return res
        # If it's a legacy dict, wrap it
        return ToolContract.wrap_result(
            name, 
            success=res.get("success", res.get("status") == "success"),
            message=res.get("message", ""),
            data=res or {},
            error=res.get("error")
        )
    except Exception as e:
        logger.exception(f"Error executing agent {name}: {e}")
        return ToolContract.wrap_result(name, success=False, error=str(e))

# --- Specialized Agents ---

@register_agent("chat_agent")
async def chat_handler(context: Dict[str, Any]) -> Dict[str, Any]:
    from backend.generation import generate_response
    from backend.redis_client import HAS_REDIS, get_cached_search, cache_search

    prompt = context.get("input", "")
    history = context.get("history", [])
    mood = context.get("mood", "philosophical")
    user_tier = context.get("user_tier", "free")
    user_id = context.get("user_id", "guest")

    # Cache check: skip for guests, skip when history is present (personalised)
    if user_id and not str(user_id).startswith("guest:") and not history:
        cache_key = hashlib.sha256(f"chat:{user_id}:{mood}:{prompt.strip().lower()}".encode()).hexdigest()[:20]
        cached = get_cached_search(cache_key)
        if cached:
            logger.info(f"chat_agent cache HIT for user={user_id}")
            cached["cache_hit"] = True
            return cached

    response = await generate_response(
        prompt=prompt,
        history=history,
        mood=mood,
        user_tier=user_tier
    )
    
    return ToolContract.wrap_result(
        "chat_agent",
        success=True,
        message=response
    )

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
        return ToolContract.wrap_result(
            "image_agent",
            success=False,
            error=result.get("error", "Studio failed.")
        )

    return ToolContract.wrap_result(
        "image_agent",
        success=True,
        message=f"I have visualized your concept: '{message}'. The masterpiece is being rendered.",
        data={"job_id": result.get("job_id")}
    )

@register_agent("search_agent")
async def search_handler(context: Dict[str, Any]) -> Dict[str, Any]:
    """Uses LLM to perform deep thematic research / search simulation.
    
    PHASE 48: Response caching — identical search queries return cached results
    for 30 minutes, avoiding redundant LLM API calls.
    """
    from backend.generation import _async_call_llm_api
    from backend.payments import use_credits
    from backend.redis_client import get_cached_search, cache_search

    user_id = context.get("user_id", "guest")
    topic = context.get("input", "the unknown")

    # ── Cache read: skip credit deduction on cache hit ────────────────────────
    cache_key = hashlib.sha256(f"search:{topic.strip().lower()}".encode()).hexdigest()[:20]
    cached = get_cached_search(cache_key)
    if cached:
        logger.info(f"search_agent cache HIT for topic='{topic[:40]}'")
        cached["cache_hit"] = True
        return cached

    # Phase 4: Tier Enforcement (Search requires 'search' feature)
    user_tier = context.get("user_tier", "free")
    from backend.config import TIERS
    tier_config = TIERS.get(user_tier, TIERS["free"])
    if "search" not in tier_config.get("features", []):
         return {
            "status": "error",
            "message": "The Deep Search agent requires a Pro or Creator subscription.",
            "agent": "search_agent",
            "retryable": False
        }

    # Phase 4: Credit Deduction (Search = 1 credit) — only on cache miss
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

    return ToolContract.wrap_result(
        "search_agent",
        success=True,
        message=search_results or "The collective knowledge is silent on this matter."
    )

@register_agent("code_agent")
async def code_handler(context: Dict[str, Any]) -> Dict[str, Any]:
    """Generates clean, functional code with architectural explanations."""
    from backend.generation import _async_call_llm_api
    from backend.payments import use_credits
    
    user_id = context.get("user_id", "guest")
    task = context.get("input", "")
    
    # Phase 4: Tier Enforcement (Code requires 'high_reasoning' feature)
    user_tier = context.get("user_tier", "free")
    from backend.config import TIERS
    tier_config = TIERS.get(user_tier, TIERS["free"])
    if "high_reasoning" not in tier_config.get("features", []):
         return {
            "status": "error",
            "message": "The Logic Architect (Code Agent) requires a Pro or Creator subscription.",
            "agent": "code_agent",
            "retryable": False
        }

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
    
    return ToolContract.wrap_result(
        "code_agent",
        success=True,
        message=code_output or "I could not construct the logic you requested."
    )

