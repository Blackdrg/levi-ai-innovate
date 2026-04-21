"""
Sovereign Brain API v7.
Strategic intent detection and engine routing for the LEVI-AI OS.
Bridges to the FusionEngine for high-fidelity synthesis.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field

from backend.auth import SovereignAuth, UserIdentity
from backend.core.planner import detect_intent
from backend.core.fusion_engine import FusionEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Brain"])

# Initialize production brain components
fusion = FusionEngine()

class BrainRequest(BaseModel):
    message: str = Field(..., description="The user input to analyze")
    session_id: Optional[str] = None

async def get_sovereign_identity(request: Request) -> UserIdentity:
    """Dependency to extract and verify the Sovereign Identity pulse."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return UserIdentity(user_id=f"guest_{request.client.host if request.client else 'local'}")
    
    token = auth_header.split(" ")[1]
    identity = SovereignAuth.verify_token(token)
    if not identity:
        raise HTTPException(status_code=401, detail="Sovereign Identity pulse invalid.")
    return identity

@router.post("")
async def brain_strategy_endpoint(
    request: BrainRequest,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    High-fidelity intent detection and strategic synthesis.
    Determines the optimal cognitive path for the OS.
    """
    logger.info(f"[BrainAPI] Strategic analysis started for {identity.user_id}")
    
    try:
        import asyncio
        
        from backend.utils.runtime_tasks import create_tracked_task
        
        # 1 & 2. Parallel Strategic Intent Detection & Synthesis
        intent_task = create_tracked_task(detect_intent(request.message), name="detect_intent")
        fusion_task = create_tracked_task(
            FusionEngine.fuse_results(
                query=request.message,
                results=[{"agent": "KNOWLEDGE", "message": "Analyzing multidimensional resonance...", "success": True}],
                lang="en",
                fast_mode=True
            ),
            name="fusion_task"
        )
        
        intent_data, fusion_result = await asyncio.gather(intent_task, fusion_task)
        
        return {
            "strategy": intent_data.intent_type,
            "confidence": intent_data.confidence_score,
            "insight": fusion_result,
            "session_id": request.session_id,
            "status": "active"
        }
    except Exception as e:
        logger.error(f"[BrainAPI] Strategic failure: {e}")
        return {"status": "error", "message": "The cosmic brain pulse is out of sync."}

@router.get("/stream")
async def strategy_stream(
    message: str,
    session_id: Optional[str] = None,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    [Phase 2] Sovereign Cognitive Streaming.
    Wires the user directly into the agentic thinking-loop.
    """
    from fastapi.responses import StreamingResponse
    from backend.engines.brain.orchestrator import orchestrator as brain_orchestrator
    import json
    
    async def event_generator():
        async for update in brain_orchestrator.stream_request(identity.user_id, message):
            yield f"data: {json.dumps(update)}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
