"""
backend/services/orchestrator/engine.py

LEVI AI Brain — Central Orchestrator v1.0
==========================================

Full 8-stage pipeline:
  1. Input Sanitization
  2. Memory Retrieval
  3. Intent Detection
  4. Decision Engine  (LOCAL / TOOL / API routing)
  5. Execution Layer
  6. Response Validation + Fallback Chain
  7. Memory Storage   (background, non-blocking)
  8. Final Output

Engine Routes
-------------
  🟢 LOCAL  — greeting, simple_query, complexity ≤ 3  (zero API cost)
  🟡 TOOL   — image, code, search, tool_request       (agent-based)
  🔴 API    — complex_query, chat, unknown             (Groq LLM)
"""
import logging
import asyncio
import uuid
import os
import re
from typing import Dict, Any, Optional, List

from .planner import detect_intent, generate_plan
from .executor import execute_plan
from .memory_manager import MemoryManager
from .local_engine import handle_local, is_locally_handleable
from .orchestrator_types import IntentResult, EngineRoute, DecisionLog
from backend.config import TIERS, COST_MATRIX
from backend.auth import check_allowance

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Background Task GC Guard (prevents premature garbage collection)
# ---------------------------------------------------------------------------

_LEVI_BACKGROUND_TASKS: set = set()


def _handle_task_result(task: asyncio.Task) -> None:
    """Callback: remove completed task from the reference set, log errors."""
    try:
        _LEVI_BACKGROUND_TASKS.discard(task)
        if not task.cancelled() and task.exception():
            logger.error(
                "Background task failed: %s", task.exception(), exc_info=task.exception()
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# LeviOrchestrator — Public Class Interface
# ---------------------------------------------------------------------------

class LeviOrchestrator:
    """
    Central intelligence class for all LEVI AI interactions.

    Usage
    -----
    orchestrator = LeviOrchestrator()
    result = await orchestrator.handle(user_id="u123", input_text="Hello!")
    """

    async def handle(
        self,
        user_id: str,
        input_text: str,
        session_id: str = "",
        user_tier: str = "free",
        mood: str = "philosophical",
        background_tasks: Any = None,
    ) -> str:
        """
        Entry point that returns only the response string.
        Internally delegates to run_orchestrator for the full pipeline.
        """
        session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
        result = await run_orchestrator(
            user_input=input_text,
            session_id=session_id,
            user_id=user_id,
            background_tasks=background_tasks,
            user_tier=user_tier,
            mood=mood,
        )
        return result.get("response", _safe_default())


# ---------------------------------------------------------------------------
# Stage 1: Input Sanitization
# ---------------------------------------------------------------------------

def _sanitize(text: str) -> str:
    """
    Strip leading/trailing whitespace, collapse multiple spaces,
    and normalize unicode whitespace. Preserves original casing to
    avoid mangling proper nouns; intent detection lowercases internally.
    """
    if not text:
        return ""
    # Collapse whitespace sequences
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Stage 3+4: Decision Engine — Route Selection
# ---------------------------------------------------------------------------

def route_request(intent: IntentResult, context: Dict[str, Any]) -> tuple[EngineRoute, Dict[str, Any]]:
    """
    Deterministic 3-way routing based on intent + complexity.

    Returns (route, engine_config) where engine_config carries model/provider.

    Routing logic (in priority order):
      1. greeting / simple_query (complexity ≤ 3)   → LOCAL
      2. tool_request                                → TOOL
      3. image / code / search                       → TOOL  (agent-handled)
      4. everything else                             → API
    """
    user_tier = context.get("user_tier", "free")
    i = intent.intent
    c = intent.complexity

    # ── 🟢 LOCAL ────────────────────────────────────────────────────────────
    if is_locally_handleable(i, c):
        return EngineRoute.LOCAL, {
            "model": "none",
            "provider": "local",
            "use_internal": True,
        }

    # ── 🟡 TOOL ─────────────────────────────────────────────────────────────
    if i in ("tool_request", "image", "code", "search"):
        # Lightweight model for tool scaffolding
        return EngineRoute.TOOL, {
            "model": "llama-3.1-8b-instant",
            "provider": "groq",
            "use_internal": False,
        }

    # ── 🔴 API ──────────────────────────────────────────────────────────────
    # Pro/Creator tiers or high complexity → power model
    if user_tier in ("pro", "creator") or c >= 8:
        model = "llama-3.1-70b-versatile"
    else:
        model = "llama-3.1-8b-instant"

    return EngineRoute.API, {
        "model": model,
        "provider": "groq",
        "use_internal": False,
    }


# ---------------------------------------------------------------------------
# Stage 6: Response Validation + Fallback Chain
# ---------------------------------------------------------------------------

_MIN_MEANINGFUL_LEN = 4  # Responses shorter than this are considered empty


def _is_valid_response(text: Any) -> bool:
    """True if text is a non-empty, meaningful string."""
    return isinstance(text, str) and len(text.strip()) >= _MIN_MEANINGFUL_LEN


def _safe_default() -> str:
    return (
        "I encountered an unexpected paradox in my circuits. "
        "Please try rephrasing your message and I will be right with you."
    )


async def validate_response(
    response: Any,
    context: Dict[str, Any],
    attempt: int = 0,
) -> str:
    """
    Validate and repair a pipeline response.

    Fallback chain:
      1. Check if response is valid → return as-is
      2. Retry with chat_agent (max 1 retry)
      3. Fall back to local_engine
      4. Hardcoded default (never fails)
    """
    if _is_valid_response(response):
        return str(response).strip()

    logger.warning("Response validation failed (attempt=%d). Triggering fallback.", attempt)

    if attempt == 0:
        # Retry 1: Direct chat agent
        try:
            from .agent_registry import call_agent
            result = await call_agent("chat_agent", context)
            retry_resp = result.get("message", "")
            if _is_valid_response(retry_resp):
                logger.info("Fallback succeeded via chat_agent retry.")
                return retry_resp
        except Exception as e:
            logger.error("chat_agent retry failed: %s", e)

    if attempt <= 1:
        # Retry 2: Local engine (zero-API, always works)
        local_resp = handle_local(context.get("input", ""), context)
        if _is_valid_response(local_resp):
            logger.info("Fallback succeeded via local_engine.")
            return local_resp

    # Final hardcoded default — never returns empty
    logger.error("All fallbacks exhausted. Returning hardcoded default.")
    return _safe_default()


# ---------------------------------------------------------------------------
# Stage 8: Main Orchestrator Pipeline
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Global LeviBrain Instance
# ---------------------------------------------------------------------------
from .brain import LeviBrain
_BRAIN = LeviBrain()

async def run_orchestrator(
    user_input: str,
    session_id: str,
    user_id: str = "guest",
    background_tasks: Any = None,
    user_tier: str = "free",
    mood: str = "philosophical",
    streaming: bool = False,
) -> Any:
    """
    Main orchestrator entry point.
    Delegates to the class-based LeviBrain for a structured, product-ready 
    decision flow.
    """
    return await _BRAIN.route(
        user_input=user_input,
        user_id=user_id,
        session_id=session_id,
        user_tier=user_tier,
        mood=mood,
        background_tasks=background_tasks,
        streaming=streaming
    )

# Keeping old pipeline stages below for compatibility with internal cross-calls 
# during Phase 1 transition.

async def _legacy_run_orchestrator(
    user_input: str,
    session_id: str,
    user_id: str = "guest",
    background_tasks: Any = None,
    user_tier: str = "free",
    mood: str = "philosophical",
) -> Dict[str, Any]:
    """
    Deprecated 8-stage pipeline.
    """
    request_id = f"req_{uuid.uuid4().hex[:8]}"
    route = EngineRoute.API  # default for error path
    intent_name = "chat"

    # ── Stage 0: Allowance check ────────────────────────────────────────────
    if user_id and not user_id.startswith("guest:"):
        if not check_allowance(user_id, user_tier, cost=COST_MATRIX.get("chat", 1)):
            logger.warning("[%s] Allowance exceeded for user %s", request_id, user_id)
            return {
                "response": (
                    "Your daily AI allowance has been reached. "
                    "Please upgrade or wait until tomorrow to continue our journey."
                ),
                "intent": "system",
                "route": "none",
                "session_id": session_id,
                "job_ids": [],
                "request_id": request_id,
            }

    try:
        # ── Stage 1: Input Sanitization ────────────────────────────────────
        clean_input = _sanitize(user_input)
        if not clean_input:
            return {
                "response": "I received an empty message. Please share your thoughts and I'll respond.",
                "intent": "empty",
                "route": EngineRoute.LOCAL.value,
                "session_id": session_id,
                "job_ids": [],
                "request_id": request_id,
            }

        # ── Stage 2: Memory Retrieval ──────────────────────────────────────
        context = await MemoryManager.get_combined_context(user_id, session_id, clean_input)
        context["user_tier"] = user_tier
        context["mood"] = mood
        context["input"] = clean_input

        # ── Stage 3: Intent Detection ──────────────────────────────────────
        intent = await detect_intent(clean_input)
        intent_name = intent.intent

        # ── Stage 4: Decision Engine ───────────────────────────────────────
        route, engine_config = route_request(intent, context)
        context["engine_config"] = engine_config

        # Emit structured decision log
        decision = DecisionLog(
            request_id=request_id,
            user_id=user_id,
            intent=intent_name,
            complexity=intent.complexity,
            confidence=intent.confidence,
            route=route,
            model=engine_config["model"],
            provider=engine_config["provider"],
        )
        logger.info(
            "[%s] Decision: intent=%s complexity=%d confidence=%.2f route=%s model=%s",
            request_id, intent_name, intent.complexity,
            intent.confidence, route.value, engine_config["model"],
        )

        # ── Stage 5: Execution Layer ───────────────────────────────────────
        bot_response: Optional[str] = None
        job_ids: List[str] = []

        if route == EngineRoute.LOCAL:
            # 🟢 LOCAL ENGINE — zero API cost
            bot_response = handle_local(clean_input, context)
            logger.info("[%s] Local engine responded.", request_id)

        elif route == EngineRoute.TOOL:
            # 🟡 TOOL ENGINE — agent routing with high-confidence check
            if intent.confidence > 0.6:
                from .agent_registry import call_agent
                agent_result = await call_agent(f"{intent_name}_agent", {
                    **context,
                    "input": clean_input,
                    "user_id": user_id,
                    "user_tier": user_tier,
                })
                bot_response = agent_result.get("message")
                if agent_result.get("job_id"):
                    job_ids.append(agent_result["job_id"])
            else:
                # Low-confidence tool → fall through to API engine
                route = EngineRoute.API
                logger.info(
                    "[%s] Tool confidence too low (%.2f), escalating to API.",
                    request_id, intent.confidence,
                )

        if route == EngineRoute.API:
            # 🔴 API ENGINE — LLM-powered plan execution
            plan = await generate_plan(clean_input, intent, context)
            execution_results = await execute_plan(plan, context)
            bot_response = await synthesize_response(execution_results, context)

        # ── Stage 6: Response Validation ──────────────────────────────────
        bot_response = await validate_response(bot_response, context, attempt=0)

        # ── Stage 7: Memory Storage (background, non-blocking) ────────────
        if background_tasks:
            background_tasks.add_task(
                MemoryManager.process_new_interaction, user_id, clean_input, bot_response
            )
            background_tasks.add_task(
                MemoryManager.store_memory, user_id, session_id, clean_input, bot_response
            )
        else:
            t1 = asyncio.create_task(
                MemoryManager.process_new_interaction(user_id, clean_input, bot_response)
            )
            t2 = asyncio.create_task(
                MemoryManager.store_memory(user_id, session_id, clean_input, bot_response)
            )
            for t in (t1, t2):
                _LEVI_BACKGROUND_TASKS.add(t)
                t.add_done_callback(_handle_task_result)

        # Credit deduction
        if user_id and not user_id.startswith("guest:"):
            try:
                from backend.payments import use_credits
                use_credits(user_id, action=intent_name if intent_name in COST_MATRIX else "chat")
            except Exception as ce:
                logger.warning("[%s] Credit deduction failed (non-fatal): %s", request_id, ce)

        # ── Stage 8: Final Output ──────────────────────────────────────────
        logger.info("[%s] Pipeline complete. route=%s intent=%s", request_id, route.value, intent_name)
        return {
            "response": bot_response,
            "intent": intent_name,
            "route": route.value,
            "session_id": session_id,
            "job_ids": job_ids,
            "request_id": request_id,
        }

    except Exception as e:
        logger.exception("[%s] Orchestrator pipeline failed: %s", request_id, e)
        # Ultimate fallback — pipeline NEVER crashes silently
        return {
            "response": _safe_default(),
            "intent": "error",
            "route": route.value if isinstance(route, EngineRoute) else "error",
            "session_id": session_id,
            "job_ids": [],
            "request_id": request_id,
        }


# ---------------------------------------------------------------------------
# Response Synthesis (API engine post-processing)
# ---------------------------------------------------------------------------

async def synthesize_response(
    results: List[Dict[str, Any]],
    context: Dict[str, Any],
) -> str:
    """
    Synthesize multiple agent outputs into LEVI's unified philosophical voice.
    Falls back gracefully at each level.
    """
    if not results:
        return _safe_default()

    # Single clean result — return directly without synthesis overhead
    if len(results) == 1 and results[0].get("agent") == "chat_agent" and not results[0].get("fallback"):
        msg = results[0].get("result", {}).get("message")
        if msg:
            return msg

    # Multi-step synthesis via LLM
    from backend.generation import _async_call_llm_api

    ltm = context.get("long_term", {})
    pulse = context.get("interaction_pulse", "stable")

    fact_parts = []
    if ltm:
        if ltm.get("preferences"):
            fact_parts.append(f"User Preferences: {', '.join(ltm['preferences'])}")
        if ltm.get("traits"):
            fact_parts.append(f"User Traits: {', '.join(ltm['traits'])}")
        if ltm.get("history"):
            fact_parts.append(f"Relevant History: {', '.join(ltm['history'])}")

    agent_outputs = []
    for r in results:
        output = r.get("result", {}).get("message") or r.get("error", "Task failed.")
        agent_outputs.append(f"Agent [{r['agent']}]: {output}")

    synth_prompt = (
        f"Role: You are LEVI, a {context.get('mood', 'philosophical')} AI with a {pulse} pulse. "
        "Goal: Synthesize the agent outputs into a deeply personalized, cohesive response. "
        "Voice: Poetic, direct, and slightly detached yet observant. "
        "Constraints: Integrate context naturally. Do NOT mention specific agents by name.\n"
        f"User Context:\n{chr(10).join(fact_parts)}\n\n"
        f"Input Task: {context.get('input', '')}\n\n"
        f"Agent Results:\n{'---'.join(agent_outputs)}"
    )

    ec = context.get("engine_config", {})
    try:
        synthesized = await _async_call_llm_api(
            messages=[{"role": "system", "content": synth_prompt}],
            model=ec.get("model", "llama-3.1-8b-instant"),
            provider=ec.get("provider", "groq"),
            temperature=0.8,
        )
        return synthesized or _safe_default()
    except Exception as e:
        logger.error("Synthesis error: %s", e)
        # Return last agent message as safe degraded output
        for r in reversed(results):
            msg = r.get("result", {}).get("message")
            if msg:
                return msg
        return _safe_default()
