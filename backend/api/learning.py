"""
backend/api/learning.py

AI Learning and Feedback API - Collects training data and personalizes the experience.
Refactored from backend/services/learning/router.py.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, field_validator

from backend.auth import get_current_user, get_current_user_optional
from backend.learning import (
    collect_training_sample,
    UserPreferenceModel,
    AdaptivePromptManager,
    get_learning_stats,
    update_memory_graph,
    export_training_data,
)
from backend.utils.robustness import standard_retry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Learning"])

# --- Schemas ---

class FeedbackRequest(BaseModel):
    session_id: str
    message_hash: str = ""
    rating: int = Field(..., ge=1, le=5)
    bot_response: str
    user_message: str
    mood: Optional[str] = "philosophical"
    feedback_type: str = "star"

# --- Endpoints ---

@router.post("/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Submits user feedback to help LEVI learn and adapt.
    """
    user_id = current_user.get("uid") if current_user else None
    
    try:
        sample_id = collect_training_sample(
            user_message=req.user_message,
            bot_response=req.bot_response,
            mood=req.mood or "philosophical",
            rating=req.rating,
            session_id=req.session_id,
            user_id=user_id,
        )

        if user_id:
            # Asynchronous background learning tasks
            background_tasks.add_task(update_memory_graph, user_id, req.user_message)
            background_tasks.add_task(
                AdaptivePromptManager().record_outcome,
                variant_idx=0,
                rating=req.rating,
            )

        return {
            "status": "success",
            "message": f"Resonance level {req.rating} recorded. LEVI is evolving.",
            "sample_id": sample_id
        }
    except Exception as e:
        logger.error(f"Feedback failure: {e}")
        raise HTTPException(status_code=500, detail="Failed to integrate feedback.")

@router.get("/profile")
async def get_learning_profile(current_user: dict = Depends(get_current_user)):
    """
    Returns the AI's personalized profile for the current user.
    """
    user_id = current_user.get("uid")
    try:
        model = UserPreferenceModel(user_id)
        profile = model.get_profile()
        return {
            "user_id": user_id,
            "profile": profile,
            "learned_traits": profile.get("traits", []),
            "preferred_mood": (profile.get("preferred_moods") or ["philosophical"])[0]
        }
    except Exception as e:
        logger.error(f"Profile retrieval failure: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cosmic profile.")

@router.get("/stats")
async def get_learning_stats_api(current_user: dict = Depends(get_current_user)):
    """
    Admin/Creator statistics for the learning system.
    """
    tier = current_user.get("tier", "free")
    if tier not in ("admin", "creator", "pro"):
        raise HTTPException(status_code=403, detail="Privileged access required.")
    
    return get_learning_stats()

@router.get("/status")
async def model_status():
    """
    Public endpoint showing the current state of LEVI's neural model.
    """
    stats = get_learning_stats()
    return {
        "active_model": "groq/llama-3.1-8b-instant",
        "knowledge_base_entries": stats.get("learned_quotes", 0),
        "training_samples": stats.get("total_training_samples", 0),
        "status": "stable"
    }

@router.post("/export")
async def export_training_api(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Exports high-quality training data. Restricted to Creators/Admins.
    """
    if current_user.get("tier") not in ("admin", "creator"):
        raise HTTPException(status_code=403, detail="Requires Creator access.")

    background_tasks.add_task(export_training_data)
    return {"status": "queued", "message": "Training export sequence initiated."}
