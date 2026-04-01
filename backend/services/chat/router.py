"""
backend/services/chat/router.py

Chat endpoint — true Groq token-by-token streaming for API-routed requests,
simulated streaming for LOCAL/TOOL routes, and 30-min response caching for
identical repeated queries.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from backend.utils.exceptions import LEVIException
from fastapi.responses import StreamingResponse
from typing import Optional, AsyncGenerator, Dict, Any
import logging
import json
import asyncio
import hashlib

from backend.services.learning.models import ChatMessage, _INJECTION_PATTERNS
from backend.auth import get_current_user_optional
from backend.db.redis_client import is_rate_limited, incr_daily_ai_spend, get_daily_ai_spend, HAS_REDIS
from backend.db.firestore_db import update_analytics
from backend.services.orchestrator import run_orchestrator
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Chat"])

# ── Response Cache (30 min TTL) ──────────────────────────────────────────────

_CACHE_TTL = 1800  # 30 minutes

def _make_cache_key(user_id: str, message: str, mood: str) -> str:
    """Create a cache key for deduplicated responses."""
    raw = f"{user_id}::{mood}::{message.strip().lower()}"
    return f"chat_cache:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def _get_cached_response(key: str) -> Optional[Dict]:
    """Return cached orchestrator result dict, or None on miss."""
    if not HAS_REDIS:
        return None
    try:
        from backend.db.redis_client import r as redis_client
        raw = redis_client.get(key)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


def _cache_response(key: str, result: Dict) -> None:
    """Store orchestrator result in Redis for 30 minutes."""
    if not HAS_REDIS:
        return
    try:
        from backend.db.redis_client import r as redis_client
        redis_client.setex(key, _CACHE_TTL, json.dumps(result, default=str))
    except Exception:
        pass


# ── Streaming Generators ─────────────────────────────────────────────────────

async def _true_groq_stream(
    user_input: str,
    session_id: str,
    user_tier: str,
    mood: str,
    orchestrator_data: Dict[str, Any],
) -> AsyncGenerator[str, None]:
    """
    True Groq token-by-token streaming for API-route requests.
    Sends orchestrator metadata with the first chunk, then streams tokens live.
    """
    from backend.generation import async_stream_llm_response
    from backend.services.orchestrator.engine import route_request
    from backend.services.orchestrator.planner import detect_intent
    from backend.generation import _get_random_persona, _build_dynamic_system_prompt

    # Build messages for the streaming call (same persona/history logic)
    intent = await detect_intent(user_input)
    persona = _get_random_persona(mood)
    system_prompt = _build_dynamic_system_prompt(persona)

    history = orchestrator_data.get("history", [])
    messages = [{"role": "system", "content": system_prompt}]
    for turn in (history[-4:] if len(history) > 4 else history):
        if turn.get("user"):
            messages.append({"role": "user", "content": turn["user"]})
        if turn.get("bot"):
            messages.append({"role": "assistant", "content": turn["bot"]})
    messages.append({"role": "user", "content": user_input})

    # Determine model from route
    ec = orchestrator_data.get("engine_config", {})
    model = ec.get("model", "llama-3.1-8b-instant")

    # First chunk: send metadata
    metadata = {
        "intent": orchestrator_data.get("intent", "chat"),
        "route": orchestrator_data.get("route", "api"),
        "session_id": session_id,
        "request_id": orchestrator_data.get("request_id", ""),
        "job_ids": orchestrator_data.get("job_ids", []),
        "streaming": True,
    }
    first_chunk = {"choices": [{"delta": {"content": ""}}], "metadata": metadata}
    yield f"data: {json.dumps(first_chunk)}\n\n"

    # Stream tokens live from Groq
    async for token in async_stream_llm_response(
        messages=messages,
        model=model,
        temperature=persona.get("temperature", 0.85),
        max_tokens=300,
    ):
        chunk = {"choices": [{"delta": {"content": token}}]}
        yield f"data: {json.dumps(chunk)}\n\n"

    yield "data: [DONE]\n\n"


async def _real_local_stream(stream: AsyncGenerator[str, None], metadata: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """
    Real token-by-token streaming for LOCAL route.
    """
    first = True
    async for token in stream:
        chunk = {
            "choices": [{"delta": {"content": token}}],
            "metadata": metadata if first else {},
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        first = False
    yield "data: [DONE]\n\n"


async def _simulated_stream(orchestrator_data: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """
    Simulated word-by-word streaming for TOOL route responses.
    These routes compute the full response instantly, so we simulate the typing feel.
    """
    response_text = orchestrator_data.get("response", "")
    metadata = {k: v for k, v in orchestrator_data.items() if k not in ("response",)}

    words = response_text.split(" ")
    for i, word in enumerate(words):
        chunk = {
            "choices": [{"delta": {"content": word + (" " if i < len(words) - 1 else "")}}],
            "metadata": metadata if i == 0 else {},
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0.012)
    yield "data: [DONE]\n\n"


# ── Unified Sovereign Streamer ──────────────────────────────────────────────

async def sovereign_generator(
    msg: ChatMessage,
    user_id: str,
    user_tier: str,
    background_tasks: BackgroundTasks
) -> AsyncGenerator[str, None]:
    """
    Unified SSE Generator that yields:
    1. Brain Activity (Thinking...)
    2. Decision Metadata (Route, Intent)
    3. Content Chunks (Local or Cloud)
    """
    from backend.services.orchestrator import run_orchestrator
    
    # ── 1. Brain Preparation & Activity ──
    async def _on_activity(message: str):
        event = {"type": "activity", "message": message}
        # Yielding inside the callback is tricky for generators, 
        # so we'll use a queue or shared list if needed, but 
        # for simplicity, let's just use the direct yield since 
        # run_orchestrator and the Brain were designed for this.
        # Wait: run_orchestrator currently returns the full response for non-streaming.
        # We need to make it stream its own thinking.
        pass

    # For now, let's use a simpler approach: the router calls the Brain 
    # and the Brain yields events.
    
    from backend.services.orchestrator.brain import LeviBrain
    brain = LeviBrain()
    
    queue = asyncio.Queue()
    
    async def status_callback(msg: str):
        await queue.put({"type": "activity", "message": msg})

    # Start Brain in the background
    brain_task = asyncio.create_task(brain.route(
        user_input=msg.message,
        user_id=user_id,
        session_id=msg.session_id,
        streaming=True, # We want the stream back
        status_callback=status_callback,
        user_tier=user_tier,
        mood=msg.mood or "philosophical"
    ))

    # ── 2. Consumption Loop ──
    done_thinking = False
    orch_result = None
    
    while not (done_thinking and queue.empty()):
        # Try to get activity updates while the brain is working
        try:
            # Short timeout to keep the loop moving
            update = await asyncio.wait_for(queue.get(), timeout=0.1)
            yield f"data: {json.dumps(update)}\n\n"
        except asyncio.TimeoutError:
            pass
        
        if brain_task.done() and not done_thinking:
            orch_result = brain_task.result()
            done_thinking = True
            
            # Yield Metadata immediately after thinking is done
            metadata = {k: v for k, v in orch_result.items() if k != "stream"}
            yield f"data: {json.dumps({'metadata': metadata})}\n\n"
            
            # ── 3. Response Streaming ──
            real_stream = orch_result.get("stream")
            if real_stream:
                async for token in real_stream:
                    chunk = {"choices": [{"delta": {"content": token}}]}
                    yield f"data: {json.dumps(chunk)}\n\n"
            else:
                # Simulated for tool results
                response_text = orch_result.get("response", "")
                words = response_text.split(" ")
                for i, word in enumerate(words):
                    chunk = {"choices": [{"delta": {"content": word + (" " if i < len(words) - 1 else "")}}]}
                    yield f"data: {json.dumps(chunk)}\n\n"
                    await asyncio.sleep(0.01)

    yield "data: [DONE]\n\n"

# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("")
async def chat_endpoint(
    request: Request,
    msg: ChatMessage,
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    user_id = (
        current_user.get("uid")
        if current_user
        else f"guest:{request.client.host if request.client else '127.0.0.1'}"
    )
    user_tier = current_user.get("tier", "free") if current_user else "free"

    # Rate limiting
    if is_rate_limited(str(user_id), limit=15, window=60):
        raise LEVIException(
            "Too many messages. Please wait.", status_code=429, error_code="RATE_LIMIT_EXCEEDED"
        )
    
    # ── Native Sovereign Streaming ──
    # All production requests now use the Unified Generator to ensure 'Brain Activity' visibility.
    return StreamingResponse(
        sovereign_generator(msg, str(user_id), user_tier, background_tasks),
        media_type="text/event-stream"
    )
