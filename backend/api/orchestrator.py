"""
Sovereign Orchestration Gateway v7.
Primary interface for the LEVI-AI OS Brain.
Bridges REST/SSE requests to the production-grade BrainOrchestrator.
"""

import logging
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.auth import get_current_user
from backend.main import orchestrator as brain

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Sovereign Orchestration"])

class MissionRequest(BaseModel):
    message: str = Field(..., description="Mission objective")
    mode: str = "AUTONOMOUS"

@router.post("/mission")
async def create_cognitive_mission(
    request: MissionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Sovereign v14.2.0: Strategic Mission Initialization.
    Dispatches a vision to the Brain and begins the DAG wave.
    """
    user_id = current_user.get("uid") or current_user.get("id")
    logger.info(f"[Orchestrator] Strategic mission started for {user_id}")
    
    try:
        mission = await brain.create_mission(
            user_id=user_id,
            objective=request.message,
            mode=request.mode
        )
        return mission
    except Exception as e:
        logger.error(f"[Orchestrator] Creation failure: {e}")
        raise HTTPException(status_code=500, detail="The cosmic brain encountered an creation anomaly.")

@router.get("/mission/{mission_id}")
async def get_mission_status(
    mission_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Returns the current state and checkpoint of a mission."""
    user_id = current_user.get("uid") or current_user.get("id")
    mission = await brain.get_mission(mission_id, user_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found in the manifest.")
    return mission

@router.delete("/mission/{mission_id}")
async def cancel_mission(
    mission_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Inhibits an in-flight mission wave."""
    user_id = current_user.get("uid") or current_user.get("id")
    await brain.cancel_mission(mission_id, user_id)
    return {"status": "inhibited", "mission_id": mission_id}

@router.post("/chat")
async def chat_legacy_bridge(
    request: MissionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Legacy bridge for simple chat interface (Phase 6 compatible)."""
    return await create_cognitive_mission(request, current_user)
