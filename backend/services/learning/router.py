"""
backend/services/learning/router.py

LEVI Learning System — FastAPI Router
Provides endpoints for:
  - POST /feedback         : User rates a response 1-5 (explicit feedback)
  - GET  /learning/profile : User's learned AI preference profile
  - GET  /learning/stats   : Learning system analytics (pro/creator/admin)
  - GET  /model/status     : Which model is active right now (public)
  - POST /model/export     : Trigger training data export (creator/admin)
"""
import logging
import hashlib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, field_validator
from backend.services.learning.models import FeedbackRequest

from backend.auth import get_current_user, get_current_user_optional
from backend.services.learning.logic import (
    collect_training_sample,
    UserPreferenceModel,
    AdaptivePromptManager,
    get_learning_stats,
    update_memory_graph,
    export_training_data,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Learning"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

# Pydantic Schemas moved to backend/models.py


# ── Explicit Feedback ─────────────────────────────────────────────────────────

@router.post("/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    User rates a response 1-5.
    - Stores a training sample in Firestore immediately.
    - High-quality responses (4+) are added to the knowledge base.
    - Memory graph is updated in the background.
    """
    user_id: Optional[str] = current_user.get("uid") if current_user else None

    try:
        sample_id = collect_training_sample(
            user_message=req.user_message,
            bot_response=req.bot_response,
            mood=req.mood or "philosophical",
            rating=req.rating,
            session_id=req.session_id,
            user_id=user_id,
        )

        # Update adaptive prompt performance tracker in background
        if user_id:
            background_tasks.add_task(
                AdaptivePromptManager().record_outcome,
                variant_idx=0,
                rating=req.rating,
            )
            background_tasks.add_task(update_memory_graph, user_id, req.user_message)

        return {
            "status": "success",
            "sample_id": sample_id,
            "rating": req.rating,
            "message": f"Thank you. Your rating of {req.rating}/5 helps LEVI learn.",
        }

    except Exception as e:
        logger.error(f"Feedback submission error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to record feedback.")


# ── User Learning Profile ─────────────────────────────────────────────────────

@router.get("/learning/profile")
async def get_my_learning_profile(
    current_user: dict = Depends(get_current_user),
):
    """Returns the AI's current learned profile for this user."""
    user_id: str = current_user.get("uid", "")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user.")

    try:
        model = UserPreferenceModel(user_id)
        profile = model.get_profile()
        prompt_manager = AdaptivePromptManager()
        preferred_mood = (profile.get("preferred_moods") or ["philosophical"])[0]
        best_variant = prompt_manager.get_best_variant(preferred_mood)
        return {
            "user_id": user_id,
            "profile": profile,
            "system_prompt_preview": model.build_system_prompt(best_variant, preferred_mood)[:300] + "...",
        }
    except Exception as e:
        logger.error(f"Profile retrieval failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve learning profile.")


# ── Learning Stats ────────────────────────────────────────────────────────────

@router.get("/learning/stats")
async def get_learning_stats_route(
    current_user: dict = Depends(get_current_user),
):
    """Returns learning system statistics. Requires Pro/Creator/Admin tier."""
    tier = current_user.get("tier", "free")
    if tier not in ("admin", "creator", "pro"):
        raise HTTPException(status_code=403, detail="Learning stats require Pro or Creator tier.")
    try:
        return get_learning_stats()
    except Exception as e:
        logger.error(f"Learning stats error: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve learning stats.")


# ── Model Status (Public) ─────────────────────────────────────────────────────

@router.get("/model/status")
async def model_status():
    """Public endpoint: returns which model is powering LEVI right now."""
    try:
        stats = get_learning_stats()
        return {
            "active_model": "groq/llama-3.1-8b-instant",
            "is_fine_tuned": False,
            "training_samples_collected": stats.get("total_training_samples", 0),
            "high_quality_samples": stats.get("high_quality_samples", 0),
            "knowledge_base_entries": stats.get("learned_quotes", 0),
            "knowledge_base_health": stats.get("knowledge_base_health", "unknown"),
        }
    except Exception as e:
        logger.error(f"Model status error: {e}")
        return {"active_model": "groq/llama-3.1-8b-instant", "status": "degraded"}


# ── Training Export ───────────────────────────────────────────────────────────

@router.post("/model/export")
async def export_training(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Export high-quality training data as JSONL. Creator/Admin only."""
    tier = current_user.get("tier", "free")
    if tier not in ("admin", "creator"):
        raise HTTPException(status_code=403, detail="Requires Creator tier.")

    def _export():
        path, count = export_training_data()
        logger.info(f"Training export: {count} samples written to {path}")

    background_tasks.add_task(_export)
    return {
        "status": "queued",
        "message": "Training export queued. Data will be written to /tmp/levi_training.jsonl",
    }
