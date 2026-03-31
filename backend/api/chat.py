"""
backend/api/chat.py

Modernized Chat API - Handles real-time streaming and local caching.
Part of the production-ready LEVI-AI architecture.
"""

import logging
import json
import asyncio
import hashlib
from typing import Optional, AsyncGenerator, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse

from backend.utils.exceptions import LEVIException
from backend.models import ChatMessage, _INJECTION_PATTERNS
from backend.auth import get_current_user_optional
from backend.redis_client import is_rate_limited, get_daily_ai_spend, HAS_REDIS
from backend.services.orchestrator import run_orchestrator
from backend.utils.robustness import standard_retry, TimeoutHandler
from backend.utils.sanitization import sanitize_input

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Chat"])

# ── Cache Config ─────────────────────────────────────────────────────────────
_CACHE_TTL = 1800  # 30 minutes

def _make_cache_key(user_id: str, message: str, mood: str) -> str:
    raw = f"{user_id}::{mood}::{message.strip().lower()}"
    return f"chat_cache:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

# ── Streaming Utilities ──────────────────────────────────────────────────────

async def _stream_response(orchestrator_data: Dict[str, Any], is_live: bool = False) -> AsyncGenerator[str, None]:
    """
    Unified streaming generator.
    Handles both live chunks from LLM and simulated typing for local paths.
    """
    if is_live:
        # Phase 3: True Streaming integration
        # In Phase 1, we delegate to the existing live stream logic
        # LEVI v6: Consolidated Production Streaming Logic
        async for chunk in _true_groq_stream(
            user_input=orchestrator_data.get("user_input", ""),
            session_id=orchestrator_data.get("session_id", ""),
            user_tier=orchestrator_data.get("user_tier", "free"),
            mood=orchestrator_data.get("mood", "philosophical"),
            orchestrator_data=orchestrator_data
        ):
            yield chunk
    else:
        # Simulated stream for LOCAL/TOOL routes
        response_text = orchestrator_data.get("response", "")
        metadata = {k: v for k, v in orchestrator_data.items() if k not in ("response",)}
        
        words = response_text.split(" ")
        for i, word in enumerate(words):
            chunk = {
                "choices": [{"delta": {"content": word + (" " if i < len(words) - 1 else "")}}],
                "metadata": metadata if i == 0 else {},
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.01)
        yield "data: [DONE]\n\n"

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
    from backend.generation import async_stream_llm_response, _build_dynamic_system_prompt, _get_random_persona
    from backend.services.orchestrator.planner import detect_intent

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
        max_tokens=600,
    ):
        chunk = {"choices": [{"delta": {"content": token}}]}
        yield f"data: {json.dumps(chunk)}\n\n"

    yield "data: [DONE]\n\n"

@router.get("/history")
async def get_chat_history(
    limit: int = 20,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Fetches the latest chat history for the current user.
    """
    if not current_user:
        return {"history": []}
    
    user_id = current_user.get("uid")
    try:
        from backend.firestore_db import db as firestore
        docs = (
            firestore.collection("chat_history")
            .where("user_id", "==", user_id)
            .order_by("timestamp", direction="DESCENDING")
            .limit(limit)
            .get()
        )
        
        history = []
        for doc in reversed(list(docs)): # Reverse to show chronological order
            data = doc.to_dict()
            history.append({
                "role": data.get("role"),
                "content": data.get("content"),
                "timestamp": data.get("timestamp")
            })
            
        return {"history": history}
    except Exception as e:
        logger.error(f"History retrieval failed: {e}")
        return {"history": [], "error": str(e)}

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
        else f"guest:{request.client.host or 'anonymous'}"
    )
    user_tier = current_user.get("tier", "free") if current_user else "free"
    
    # 0. Sanitization
    msg.message = sanitize_input(msg.message)

    # 1. Protection
    if is_rate_limited(str(user_id), limit=20):
        raise LEVIException("Atmospheric pressure is too high. Please slow down.", status_code=429)

    # 2. Cache Layer
    is_streaming = request.headers.get("accept") == "text/event-stream" or msg.stream
    cache_key = _make_cache_key(str(user_id), msg.message, msg.mood or "philosophical")
    
    if HAS_REDIS and not str(user_id).startswith("guest:") and not is_streaming:
        from backend.redis_client import r as redis
        cached = redis.get(cache_key)
        if cached:
            return json.loads(cached)

    # 3. Brain Orchestration
    request_id = getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:8]}")
    
    # Phase 8: Async Queue for real-time status updates
    event_queue = asyncio.Queue()

    async def _on_status(msg: str):
        await event_queue.put({"type": "activity", "message": msg})

    # Run orchestrator in a task so we can stream queue events in parallel
    orch_task = asyncio.create_task(run_orchestrator(
        user_input=msg.message,
        session_id=msg.session_id,
        user_id=str(user_id),
        background_tasks=background_tasks,
        user_tier=user_tier,
        mood=msg.mood or "philosophical",
        streaming=is_streaming,
        request_id=request_id,
        status_callback=_on_status
    ))

    # 4. Result Processing & Streaming
    if is_streaming:
        async def _generator():
            try:
                # ── Step A: Stream Activity Events while Orchestrating ──
                while not orch_task.done() or not event_queue.empty():
                    # Check for disconnect
                    if await request.is_disconnected():
                        orch_task.cancel()
                        return

                    try:
                        # Wait for an event with a small timeout to check orch_task status
                        event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                        yield f"data: {json.dumps(event)}\n\n"
                    except asyncio.TimeoutError:
                        continue

                result = await orch_task
                
                # Standardized metadata chunk
                metadata = {k: v for k, v in result.items() if k not in ("stream", "response")}
                yield f"data: {json.dumps({'metadata': metadata})}\n\n"

                if "stream" in result:
                    # True LLM Streaming with disconnect check
                    async for token in result["stream"]:
                        if await request.is_disconnected():
                            break
                        
                        chunk = {"choices": [{"delta": {"content": token}}]}
                        yield f"data: {json.dumps(chunk)}\n\n"
                else:
                    # Simulated stream for static results (Local/Tool)
                    response_text = result.get("response", "")
                    words = response_text.split(" ")
                    for i, word in enumerate(words):
                        if await request.is_disconnected():
                            break
                        
                        content = word + (" " if i < len(words) - 1 else "")
                        chunk = {"choices": [{"delta": {"content": content}}]}
                        yield f"data: {json.dumps(chunk)}\n\n"
                        await asyncio.sleep(0.02)
                
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Streaming error for {request_id}: {e}")
                yield f"data: {json.dumps({'error': 'Stream interrupted'})}\n\n"

        return StreamingResponse(_generator(), media_type="text/event-stream")

    # Sync implementation
    result = await orch_task

    # Sync Cache Persistence
    if HAS_REDIS and not str(user_id).startswith("guest:"):
        background_tasks.add_task(redis.setex, cache_key, _CACHE_TTL, json.dumps(result, default=str))

    return result

@router.post("/stream")
async def chat_stream_endpoint(
    request: Request,
    msg: ChatMessage,
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Explicit streaming endpoint for LEVI-AI.
    """
    msg.stream = True # Force streaming
    return await chat_endpoint(request, msg, background_tasks, current_user)
