"""
backend/api/studio.py

AI Studio API - Handles image and video generation requests via Celery.
Refactored from backend/services/studio/router.py.
"""

import logging
import uuid
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from backend.utils.exceptions import LEVIException
from backend.core.orchestrator_types import Query
from backend.services.auth.logic import get_current_user_optional
from backend.db.firestore_db import db as firestore_db
from backend.services.studio.tasks import generate_image_task, generate_video_task
from backend.services.payments.logic import use_credits
from backend.db.redis_client import is_rate_limited
from backend.utils.robustness import standard_retry, TimeoutHandler
from backend.gcp_jobs import enqueue_video_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Studio"])

@router.post("/generate_image")
async def gen_image(
    request: Request, 
    req: Query, 
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Submits an image generation task to the background worker.
    """
    try:
        client_host = request.client.host if request.client else "127.0.0.1"
        user_id = current_user.get("uid") if current_user else f"guest:{client_host}"
        user_tier = current_user.get("tier", "free") if current_user else "free"
        
        # 1. Protection
        if is_rate_limited(str(user_id), limit=5, window=60):
            raise LEVIException("Atmospheric static is too high. Please wait.", status_code=429)

        # 2. Financials
        if user_id and not str(user_id).startswith("guest:"):
            use_credits(str(user_id), 1)

        # 3. Task Enqueueing
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job_data = {
            "job_id": job_id,
            "type": "image",
            "status": "queued",
            "user_id": user_id,
            "params": {"text": req.text, "mood": req.mood, "author": req.author, "custom_bg": req.custom_bg},
            "created_at": datetime.utcnow()
        }
        
        firestore_db.collection("jobs").document(job_id).set(job_data)

        if os.getenv("USE_CELERY", "true").lower() == "true":
            generate_image_task.delay(
                job_id=job_id, 
                params=job_data["params"],
                user_id=user_id,
                user_tier=user_tier
            )
        else:
            from backend.services.studio.logic import run_studio_task
            background_tasks.add_task(
                run_studio_task, 
                job_id=job_id, 
                task_type="image", 
                params=job_data["params"],
                user_id=user_id,
                user_tier=user_tier
            )

        return {"status": "queued", "task_id": job_id, "message": "Creation sequence initiated."}

    except LEVIException:
        raise
    except Exception as e:
        logger.error(f"Studio-Image failure: {e}", exc_info=True)
        raise LEVIException("Failed to manifest the image.", status_code=500)

@router.post("/generate_video")
async def gen_video(
    request: Request, 
    req: Query, 
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Submits a video synthesis task to the background worker.
    """
    try:
        client_host = request.client.host if request.client else "127.0.0.1"
        user_id = current_user.get("uid") if current_user else f"guest:{client_host}"
        user_tier = current_user.get("tier", "free") if current_user else "free"
        
        if is_rate_limited(str(user_id), limit=3, window=60):
            raise LEVIException("Cosmic flux detected. Please slow down.", status_code=429)

        if user_id and not str(user_id).startswith("guest:"):
            use_credits(str(user_id), 2)

        job_id = f"vjob_{uuid.uuid4().hex[:12]}"
        job_data = {
            "job_id": job_id,
            "type": "video",
            "status": "queued",
            "user_id": user_id,
            "params": {"text": req.text, "mood": req.mood, "author": req.author},
            "created_at": datetime.utcnow()
        }
        
        firestore_db.collection("jobs").document(job_id).set(job_data)

        if os.getenv("USE_GCP_JOBS", "false").lower() == "true":
            # Phase 50: Use GCP Cloud Run Jobs for video
            job_id = enqueue_video_task({
                "quote": req.text,
                "mood": req.mood,
                "author": req.author,
                "user_id": user_id,
                "user_tier": user_tier
            })
            if not job_id:
                raise LEVIException("GCP Job Dispatch failed.", status_code=500)
            return {"status": "queued", "task_id": job_id, "message": "Video job dispatched to Cloud Run."}

        if os.getenv("USE_CELERY", "true").lower() == "true":
            generate_video_task.delay(
                job_id=job_id, 
                params=job_data["params"],
                user_id=user_id,
                user_tier=user_tier
            )
        else:
            from backend.services.studio.logic import run_studio_task
            background_tasks.add_task(
                run_studio_task, 
                job_id=job_id, 
                task_type="video", 
                params=job_data["params"],
                user_id=user_id,
                user_tier=user_tier
            )

        return {"status": "queued", "task_id": job_id, "message": "Video synthesis sequence initiated."}

    except LEVIException:
        raise
    except Exception as e:
        logger.error(f"Studio-Video failure: {e}", exc_info=True)
        raise LEVIException("Failed to manifest the video.", status_code=500)

@router.get("/task_status/{job_id}")
async def get_task_status(job_id: str):
    """
    Polls for the status of a background generation task.
    """
    try:
        job_doc = firestore_db.collection("jobs").document(job_id).get()
        if not job_doc.exists:
            raise HTTPException(status_code=404, detail="Job footprint not found.")
        
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
            response["error"] = data.get("error", "Unknown anomaly.")
            
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Studio-Status failure: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve task status.")
