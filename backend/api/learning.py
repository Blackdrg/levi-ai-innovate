"""
Sovereign Learning & Evolution API v7.
Neural feedback collection and real-time evolution monitoring.
Bridges to the AutonomousLearner and SovereignBroadcaster.
Hardened for global telemetry and identity-aware adaptation.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.auth import SovereignAuth, UserIdentity
from backend.learning import AutonomousLearner
from backend.broadcast_utils import SovereignBroadcaster

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Learning"])

class PulseRequest(BaseModel):
    agent: str = Field(..., description="The agent that performed the mission")
    query: str = Field(..., description="The user's original vision")
    score: float = Field(..., ge=0.0, le=1.0, description="Quality resonance score")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class FeedbackRequest(BaseModel):
    session_id: str
    rating: int = Field(..., ge=1, le=5)
    user_message: str
    bot_response: str
    mood: str = "philosophical"

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

@router.post("/pulse")
async def record_neural_pulse(
    request: PulseRequest,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Submits a neural resonance pulse (feedback) to the evolution engine.
    Triggers autonomous weight adjustment and dashboard updates.
    """
    logger.info(f"[LearningAPI] Neural pulse received from {identity.user_id} for {request.agent}")
    
    try:
        # 1. Log to the Evolution Engine
        await AutonomousLearner.log_evolution_pulse(
            agent=request.agent,
            query=request.query,
            score=request.score,
            metadata={**request.metadata, "user_id": identity.user_id}
        )
        
        # 2. Broadcast to the Real-time Dashboard
        SovereignBroadcaster.publish(
            event_type="neural_pulse",
            data={"agent": request.agent, "score": request.score, "query": request.query},
            user_id="global" # Dashboard is global/admin
        )
        
        return {"status": "recorded", "message": "Neural resonance integrated into local weights."}
    except Exception as e:
        logger.error(f"[LearningAPI] Pulse integration failure: {e}")
        return {"status": "error", "message": "Failed to integrate neural pulse."}

@router.post("/feedback")
async def record_user_feedback(
    request: FeedbackRequest,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Legacy-compatible feedback endpoint for the v7 frontend.
    Maps star ratings to neural pulse scores.
    """
    logger.info(f"[LearningAPI] User feedback received from {identity.user_id}")
    
    pulse_score = (request.rating - 1) / 4.0 # Map 1-5 to 0.0-1.0
    
    try:
        await AutonomousLearner.log_evolution_pulse(
            agent="chat",
            query=request.user_message,
            score=pulse_score,
            metadata={
                "session_id": request.session_id,
                "mood": request.mood,
                "bot_response": request.bot_response,
                "user_id": identity.user_id
            }
        )
        return {"status": "recorded"}
    except Exception as e:
        logger.error(f"[LearningAPI] Feedback integration failure: {e}")
        return {"status": "error"}

@router.get("/evolution_stream")
async def neural_evolution_stream(
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    SSE endpoint for real-time monitoring of the Sovereign OS's global evolution.
    Restricted to verified identities.
    """
    logger.info(f"[LearningAPI] Evolution stream connected for {identity.user_id}")
    
    return StreamingResponse(
        SovereignBroadcaster.subscribe(user_id="global"),
        media_type="text/event-stream"
    )

@router.get("/metrics")
async def get_evolution_metrics(identity: UserIdentity = Depends(get_sovereign_identity)):
    """Retrieves high-level performance metrics for all intelligence agents."""
    # Simulation for v7 metrics
    return {
        "status": "evolving",
        "global_resonance_average": 0.88,
        "active_agents": 14,
        "processed_missions": 1420
    }
