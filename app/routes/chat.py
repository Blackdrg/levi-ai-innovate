from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from app.auth import verify_token_query
from app.brain.controller import BrainCoreController
import json, asyncio

router = APIRouter(prefix="/api/v13")
brain = BrainCoreController()

@router.get("/chat/stream")
async def stream_mission(
    prompt: str,
    fidelity_threshold: float = 0.95,
    user = Depends(verify_token_query)
):
    """
    Sovereign v13: Server-Sent Events (SSE) Mission Stream.
    Bridges the frontend React state directly to the cognitive engine's wave execution.
    """
    async def event_generator():
        try:
            # BrainCoreController.run_mission is an async generator
            async for event_type, payload in brain.run_mission(
                prompt=prompt,
                user_id=user.uid,
                fidelity_threshold=fidelity_threshold
            ):
                # Standard SSE format: "event: TYPE\ndata: JSON\n\n"
                yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
                await asyncio.sleep(0.01) # Ensure buffer flushing
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no", # Critical for Nginx/Proxy pass-through
        }
    )

@router.get("/missions")
async def get_all_missions(user = Depends(verify_token_query)):
    # Placeholder for mission history retrieval
    return {"missions": []}

@router.get("/memory/search")
async def search_memory(q: str, top_k: int = 10, user = Depends(verify_token_query)):
    results = await brain.memory.search(q, user_id=user.uid, top_k=top_k)
    return results
