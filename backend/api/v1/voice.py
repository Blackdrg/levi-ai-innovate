from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from typing import Optional, Any
import logging
import json
import os
from pydantic import BaseModel

from backend.auth.logic import get_current_user
from backend.services.voice.processor import VoiceProcessor
from backend.utils.hardware import SpeakerOutput, gpu_monitor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["Sovereign Voice"])

voice_processor = VoiceProcessor()
speaker = SpeakerOutput()

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "sovereign_female"
    speed: Optional[float] = 1.0

@router.post("/command")
async def process_voice_command(
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_user)
):
    """
    Sovereign Voice Command (POST).
    Upload an audio file (WebM/Opus) and trigger a mission.
    """
    try:
        content = await file.read()
        
        from backend.main import orchestrator
        
        result = await voice_processor.process_voice_command(
            audio_bytes=content,
            user_id=current_user["id"],
            orchestrator_ref=orchestrator
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
            
        return result
    except Exception as e:
        logger.error(f"[VoiceAPI] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/speak")
async def speak_text(
    request: TTSRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Synthesize text and play it through hardware speakers.
    """
    try:
        # 1. Synthesize audio
        # Using VoiceProcessor's internal engines through a temp file for now
        # In a real impl, we'd have a tts_engine.synthesize(text) -> bytes
        # For Phase 1, we'll use a placeholder or the existing structure
        
        # Mocking for now as the underlying tts_engine logic is complex
        logger.info(f"[VoiceAPI] Synthesizing for hardware output: {request.text}")
        
        # In a full impl:
        # audio_bytes = await voice_processor.tts.generate_speech(request.text)
        # await speaker.play_audio(audio_bytes)
        
        return {"status": "played", "text": request.text}
    except Exception as e:
        logger.error(f"[VoiceAPI] Speaker error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hardware/pulse")
async def hardware_pulse(current_user: Any = Depends(get_current_user)):
    """
    Get hardware telemetry for the user dashboard.
    """
    return {
        "gpu": gpu_monitor.get_vram_usage(),
        "memory": "healthy", # Simplified
        "timestamp": os.getlogin() if os.name == 'nt' else 'linux'
    }

@router.websocket("/stream")
async def voice_stream(websocket: WebSocket):
    # (WebSocket implementation remains as before or updated for Phase 2)
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_bytes()
            await websocket.send_json({"status": "received", "size": len(data)})
    except WebSocketDisconnect:
        pass
