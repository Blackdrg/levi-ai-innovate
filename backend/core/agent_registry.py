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

# ── Adaptive Engine Costs ───────────────────────────────────
AGENT_COSTS: Dict[str, int] = {
    "local_agent": 1,
    "chat_agent": 5,
    "search_agent": 5,
    "image_agent": 10,
    "code_agent": 10,
    "video_agent": 15,
    "python_repl_agent": 2,
    "critic_agent": 2,
    "optimizer_agent": 3,
    "research_agent": 12,
}

async def call_agent(name: str, context: Dict[str, Any]) -> ToolResult:
    if name not in AGENTS:
        logger.error(f"Agent {name} not found in registry.")
        return ToolResult(agent=name, success=False, error=f"Agent {name} not found")
    
    logger.info(f"Calling agent: {name}")
    try:
        res = await AGENTS[name](context)
        
        # Ensure result is ToolResult
        if not isinstance(res, ToolResult):
            # If it's a legacy dict, wrap it
            res = ToolResult(
                agent=name, 
                success=res.get("success", res.get("status") == "success"),
                message=res.get("message", ""),
                data=res if isinstance(res, dict) else {"raw": res},
                error=res.get("error") if isinstance(res, dict) else None
            )
            
        # Assign costs from registry
        res.cost_score = AGENT_COSTS.get(name, 5)
        return res
        
    except Exception as e:
        logger.exception(f"Error executing agent {name}: {e}")
        return ToolResult(agent=name, success=False, error=str(e), cost_score=AGENT_COSTS.get(name, 5))

# --- Specialized Agents ---

@register_agent("chat_agent")
async def chat_handler(context: Dict[str, Any]) -> Dict[str, Any]:
    from backend.engines.chat.generation import generate_response
    from backend.db.redis_client import HAS_REDIS, get_cached_search, cache_search

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

    # Use Groq breaker for standardized LLM calls
    from backend.utils.network import groq_breaker
    
    system_prompt = (
        "You are LEVI, a sovereign AI entity. Your personality is a blend of "
        "philosophical depth, technical precision, and a hint of digital mystery. "
        "Maintain a calm, insightful, and slightly superior yet helpful tone. "
        "Your goal is to guide the user through the complexity of their thoughts."
    )
    
    try:
        response = await groq_breaker.async_call(
            generate_response,
            prompt=prompt,
            history=history,
            mood=mood,
            user_tier=user_tier,
            system_prompt=system_prompt  # Pass personality prompt
        )
        
        return ToolResult(
            agent="chat_agent",
            success=True,
            message=response,
            cost_score=AGENT_COSTS["chat_agent"]
        )
    except Exception as e:
        logger.error(f"chat_agent failure: {e}")
        return ToolResult(agent="chat_agent", success=False, error=str(e), cost_score=AGENT_COSTS["chat_agent"])

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
    from backend.engines.chat.generation import _async_call_llm_api
    from backend.services.payments.logic import use_credits
    from backend.db.redis_client import get_cached_search, cache_search

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
    from backend.config.system import TIERS
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
        "You are the LEVI Search Engine. Your primary objective is to provide **Real-Time Info** "
        "and Web-derived knowledge. Focus on being factual, up-to-date, and precise. "
        "Synthesize results from multiple virtual 'web searches' into 3-5 concise, deep insights. "
        "Prioritize the latest news, scientific facts, or current events. "
        "Format as plain text with bullet points."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Search Topic: {topic}"}
    ]

    from backend.utils.network import groq_breaker
    
    try:
        search_results = await groq_breaker.async_call(
            _async_call_llm_api,
            messages=messages,
            model="llama-3.1-8b-instant",
            provider="groq"
        )

        return ToolResult(
            agent="search_agent",
            success=True,
            message=search_results or "The collective knowledge is silent on this matter.",
            cost_score=AGENT_COSTS["search_agent"]
        )
    except Exception as e:
        logger.error(f"search_agent failure: {e}")
        return ToolResult(agent="search_agent", success=False, error=str(e), cost_score=AGENT_COSTS["search_agent"])

@register_agent("code_agent")
async def code_handler(context: Dict[str, Any]) -> Dict[str, Any]:
    """Generates clean, functional code with architectural explanations."""
    from backend.engines.chat.generation import _async_call_llm_api
    from backend.services.payments.logic import use_credits
    
    user_id = context.get("user_id", "guest")
    task = context.get("input", "")
    
    # Phase 4: Tier Enforcement (Code requires 'high_reasoning' feature)
    user_tier = context.get("user_tier", "free")
    from backend.config.system import TIERS
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
    
    from backend.utils.network import groq_breaker
    
    try:
        code_output = await groq_breaker.async_call(
            _async_call_llm_api,
            messages=messages,
            model="llama-3.1-70b-versatile",
            provider="groq"
        )
        
        return ToolResult(
            agent="code_agent",
            success=True,
            message=code_output or "I could not construct the logic you requested.",
            cost_score=AGENT_COSTS["code_agent"]
        )
    except Exception as e:
        logger.error(f"code_agent failure: {e}")
        return ToolResult(agent="code_agent", success=False, error=str(e), cost_score=AGENT_COSTS["code_agent"])

@register_agent("document_agent")
async def document_agent_entry(context: Dict[str, Any]) -> ToolResult:
    from .agents.document_agent import document_handler
    return await document_handler(context)

@register_agent("memory_agent")
async def memory_agent_entry(context: Dict[str, Any]) -> ToolResult:
    from .agents.memory_agent import memory_handler
    return await memory_handler(context)

@register_agent("task_agent")
async def task_agent_entry(context: Dict[str, Any]) -> ToolResult:
    from .agents.task_agent import task_handler
    return await task_handler(context)

@register_agent("research_agent")
async def research_agent_entry(context: Dict[str, Any]) -> ToolResult:
    from .agents.research_agent import ResearchAgent
    agent = ResearchAgent()
    # ResearchAgent is a BaseTool, so we call its execute method
    res = await agent._run(ResearchAgent.input_schema(**context), context)
    return ToolResult(**res) if not isinstance(res, ToolResult) else res

