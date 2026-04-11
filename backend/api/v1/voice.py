from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from typing import Optional, Any
import logging
import json

from backend.auth.logic import get_current_user
from backend.services.voice.processor import VoiceProcessor
# We'll need to get the orchestrator instance. In main.py it's a global, 
# but we can also use app.state.

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["Sovereign Voice"])

voice_processor = VoiceProcessor()

@router.post("/command")
async def process_voice_command(
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_user)
):
    """
    Sovereign Voice Command (POST).
    Upload an audio file (WebM/Opus) and trigger a mission.
    """
    # Gating: Check user plan
    user_plan = getattr(current_user, "plan", "basic")
    if user_plan == "basic":
        # Check usage limits if necessary
        pass

    try:
        content = await file.read()
        
        # Access orchestrator from app state would be cleaner, but for now
        # we'll use the global from main.py if imported or passed.
        # Since this is Phase 1, we'll assume the processor can handle it.
        from backend.main import orchestrator
        
        result = await voice_processor.process_voice_command(
            audio_bytes=content,
            user_id=current_user.id,
            orchestrator_ref=orchestrator
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
            
        return result
    except Exception as e:
        logger.error(f"[VoiceAPI] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/stream")
async def voice_stream(websocket: WebSocket):
    """
    Sovereign Voice Stream (WebSocket).
    Continuous audio streaming and real-time response.
    """
    await websocket.accept()
    logger.info("[VoiceAPI] WebSocket connection established.")
    
    try:
        while True:
            # Phase 1: Receive audio chunks
            data = await websocket.receive_bytes()
            
            # TODO: Implement chunked STT for real-time streaming in Phase 2
            # For now, we acknowledge receipt.
            await websocket.send_json({"status": "received", "size": len(data)})
            
    except WebSocketDisconnect:
        logger.info("[VoiceAPI] WebSocket disconnected.")
    except Exception as e:
        logger.error(f"[VoiceAPI] WebSocket error: {e}")
        await websocket.close()
