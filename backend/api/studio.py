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

from pydantic import BaseModel, Field
from backend.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Studio"])

class AgentCreateRequest(BaseModel):
    name: str
    description: str
    config: dict

@router.post("/agent")
async def create_custom_agent(
    request: AgentCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Sovereign v14.2.0: Persona Handshake.
    Creates a user-defined custom agent archetype in the Resident SQL persistence.
    """
    from backend.db.models import CustomAgent
    from backend.db.postgres import PostgresDB
    import uuid
    
    user_id = current_user.get("uid") or current_user.get("id")
    
    db = PostgresDB()
    async with db.get_session() as session:
        new_agent = CustomAgent(
            agent_id=f"agent_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            name=request.name,
            description=request.description,
            config=request.config
        )
        session.add(new_agent)
        await session.commit()
        agent_id = new_agent.agent_id

    return {
        "status": "success",
        "agent_id": agent_id,
        "message": f"Agent {request.name} successfully crystallized in your personal fleet."
    }

class StudioRequest(BaseModel):
    prompt: str = Field(..., description="Visual vision for synthesis")
    style: str = "cinematic"
    aspect_ratio: str = "1:1"
    mood: str = "philosophical"

@router.post("/generate_image")
async def generate_image_mission(
    request: StudioRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Submits an image synthesis mission via the Sovereign Agent Fleet.
    """
    from backend.core.orchestrator import BrainOrchestrator
    orchestrator = BrainOrchestrator()
    
    user_id = current_user.get("uid") or current_user.get("id")
    objective = f"Render high-fidelity image: {request.prompt} in {request.style} style"
    
    mission = await orchestrator.handle_mission(
        user_input=objective,
        user_id=user_id,
        session_id=f"studio_{user_id[:8]}",
        intent_type="image",
        mood=request.mood
    )
    
    return {"status": "active", "mission_id": mission.get("request_id")}

@router.post("/generate_video")
async def generate_video_mission(
    request: StudioRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Sovereign v14.2.0: Motion Synthesis Handshake.
    Submits a video generation request to the Sovereign synthesis engine.
    """
    from backend.core.orchestrator import BrainOrchestrator
    orchestrator = BrainOrchestrator()
    
    user_id = current_user.get("uid") or current_user.get("id")
    objective = f"Synthesize motion sequence from vision: {request.prompt}"
    
    mission = await orchestrator.handle_mission(
        user_input=objective,
        user_id=user_id,
        session_id=f"studio_vid_{user_id[:8]}",
        intent_type="video",
        mood=request.mood
    )
    
    return {"status": "active", "mission_id": mission.get("request_id")}

@router.get("/mission_status/{mission_id}")
async def get_mission_status(mission_id: str, current_user: dict = Depends(get_current_user)):
    """
    Polls for the status of a Sovereign synthesis mission in the ledger.
    """
    from backend.core.execution_state import CentralExecutionState
    sm = CentralExecutionState(mission_id)
    state = sm.get_state()
    
    return {
        "id": mission_id,
        "status": state.status if state else "unknown",
        "result_url": state.metadata.get("result_url") if state else None
    }

