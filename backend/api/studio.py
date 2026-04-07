"""
Sovereign Studio API v7.
Cinematic image and video synthesis gateway for the LEVI-AI OS.
Bridges to VisualSynthesisService and VideoSynthesisService.
Hardened for asynchronous mission tracking and spectral state management.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from backend.auth import UserIdentity, get_sovereign_identity
from backend.core.agent_registry import AgentRegistry
from backend.firestore_db import db as sovereign_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Studio"])

class StudioRequest(BaseModel):
    prompt: str = Field(..., description="Visual vision for synthesis")
    style: str = "cinematic"
    aspect_ratio: str = "1:1"
    mood: str = "philosophical"

@router.post("/generate_image")
async def generate_image_mission(
    request: StudioRequest,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Submits an image synthesis mission via the Sovereign Agent Fleet.
    """
    logger.info(f"[StudioAPI] Image mission initiated for {identity.user_id}")
    
    # Standardized agent dispatch for high-fidelity synthesis
    result = await AgentRegistry.dispatch("image", {
        "prompt": request.prompt,
        "style": request.style,
        "aspect_ratio": request.aspect_ratio,
        "mood": request.mood,
        "user_id": identity.user_id
    })
    
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error or "Visual synthesis failed.")

    return {
        "mission_id": result.mission_id,
        "status": "active",
        "message": result.message,
        "data": result.data
    }

@router.post("/generate_video")
async def generate_video_mission(
    request: StudioRequest,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Submits a video synthesis mission via the Sovereign Agent Fleet.
    """
    logger.info(f"[StudioAPI] Video mission initiated for {identity.user_id}")
    
    result = await AgentRegistry.dispatch("video", {
        "prompt": request.prompt,
        "style": request.style,
        "aspect_ratio": request.aspect_ratio,
        "mood": request.mood,
        "user_id": identity.user_id
    })
    
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error or "Motion synthesis failed.")

    return {
        "mission_id": result.mission_id,
        "status": "recording",
        "message": result.message,
        "data": result.data
    }

@router.get("/mission_status/{mission_id}")
async def get_mission_status(mission_id: str):
    """
    Polls for the status of a Sovereign synthesis mission in the ledger.
    """
    mission = await sovereign_db.get_document("missions", mission_id)
    if not mission:
        # Fallback check for session-based missions
        return {"id": mission_id, "status": "pulsing", "message": "Mission pulse detected in buffer."}
        
    return {
        "id": mission_id,
        "status": mission.get("status", "unknown"),
        "progress": mission.get("progress", 0),
        "result": mission.get("result_url")
    }
