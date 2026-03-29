from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks # type: ignore
from typing import Optional
import uuid
from datetime import datetime
import os
import logging

from backend.models import Query # type: ignore
from backend.auth import get_current_user_optional # type: ignore
from backend.firestore_db import db as firestore_db, add_document # type: ignore
from backend.services.studio.tasks import generate_image_task, generate_video_task # type: ignore
from backend.payments import use_credits # type: ignore
from backend.redis_client import is_rate_limited # type: ignore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/studio", tags=["Studio"])

@router.post("/generate_image")
async def gen_image(
    request: Request, 
    req: Query, 
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    try:
        # ── Phase 40: Safe Request Access for Testing ────────────────
        client_host = request.client.host if request.client else "127.0.0.1"
        user_id = current_user.get("uid") if current_user else f"guest:{client_host}"
        user_tier = current_user.get("tier", "free") if current_user else "free"
        
        # ── Defensive: Rate Limiting ────────────────────────
        if is_rate_limited(str(user_id), limit=5, window=60):
            logger.warning(f"[RateLimit] Throttled user {user_id} in Studio (Image)")
            raise HTTPException(status_code=429, detail="Generation limit reached. Please wait a minute.")
        
        # Async Job Pattern
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job_data = {
            "job_id": job_id,
            "type": "image",
            "status": "queued",
            "user_id": user_id,
            "params": {"text": req.text, "mood": req.mood, "author": req.author, "custom_bg": req.custom_bg},
            "created_at": datetime.utcnow()
        }
        # ── Financial: Credit Check ─────────────────────────
        if user_id:
            try:
                use_credits(str(user_id), 1)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[Studio] Credit deduction failed: {e}")

        if os.getenv("USE_CELERY", "true").lower() == "true":
            generate_image_task.delay(
                job_id=job_id, 
                params=job_data["params"],
                user_id=user_id,
                user_tier=user_tier
            )
        else:
            # Fallback for local dev without Celery worker
            from backend.services.studio.logic import run_studio_task # type: ignore
            background_tasks.add_task(
                run_studio_task, 
                job_id=job_id, 
                task_type="image", 
                params=job_data["params"],
                user_id=user_id,
                user_tier=user_tier
            )

        return {"status": "queued", "task_id": job_id, "message": "Image generation started."}

    except Exception as e:
        logger.error(f"Image generation request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e), "status": "failed"})

@router.post("/generate_video")
async def gen_video(
    request: Request, 
    req: Query, 
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    try:
        # ── Phase 40: Safe Request Access for Testing ────────────────
        client_host = request.client.host if request.client else "127.0.0.1"
        user_id = current_user.get("uid") if current_user else f"guest:{client_host}"
        user_tier = current_user.get("tier", "free") if current_user else "free"
        
        # ── Defensive: Rate Limiting ────────────────────────
        if is_rate_limited(str(user_id), limit=5, window=60):
            logger.warning(f"[RateLimit] Throttled user {user_id} in Studio (Video)")
            raise HTTPException(status_code=429, detail="Generation limit reached. Please wait a minute.")

        # Async Job Pattern
        job_id = f"vjob_{uuid.uuid4().hex[:12]}"
        job_data = {
            "job_id": job_id,
            "type": "video",
            "status": "queued",
            "user_id": user_id,
            "params": {"text": req.text, "mood": req.mood, "author": req.author},
            "created_at": datetime.utcnow()
        }
        # ── Financial: Credit Check ─────────────────────────
        if user_id:
            try:
                use_credits(str(user_id), 2)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[Studio] Credit deduction failed: {e}")

        if os.getenv("USE_CELERY", "true").lower() == "true":
            generate_video_task.delay(
                job_id=job_id, 
                params=job_data["params"],
                user_id=user_id,
                user_tier=user_tier
            )
        else:
             # Fallback
            from backend.services.studio.logic import run_studio_task # type: ignore
            background_tasks.add_task(
                run_studio_task, 
                job_id=job_id, 
                task_type="video", 
                params=job_data["params"],
                user_id=user_id,
                user_tier=user_tier
            )

        return {"status": "queued", "task_id": job_id, "message": "Video synthesis started."}

    except Exception as e:
        logger.error(f"Video generation request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e), "status": "failed"})

@router.get("/task_status/{job_id}")
async def get_task_status(job_id: str):
    """Poll for the status of a generation job."""
    try:
        job_doc = firestore_db.collection("jobs").document(job_id).get()
        if not job_doc.exists:
            raise HTTPException(status_code=404, detail="Job not found")
        
        data = job_doc.to_dict()
        status = data.get("status", "queued")
        
        response = {
            "status": status,
            "task_id": job_id,
        }
        
        if status == "completed":
            response["result"] = {
                "url": data.get("url"),
                "engine": data.get("engine")
            }
        elif status == "failed":
            response["error"] = data.get("error", "Unknown error")
            
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
