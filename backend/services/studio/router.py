from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks # type: ignore
from typing import Optional
import uuid
from datetime import datetime
import os

from backend.models import Query # type: ignore
from backend.auth import get_current_user_optional # type: ignore
from backend.firestore_db import db as firestore_db, add_document # type: ignore
from backend.services.studio.tasks import generate_image_task, generate_video_task # type: ignore

router = APIRouter(prefix="/studio", tags=["Studio"])

def is_rate_limited(user_id: str):
    # Simplified rate limiting check for internal routing
    # This will be handled more robustly in the Gateway
    return False

@router.post("/generate_image")
async def gen_image(
    request: Request, 
    req: Query, 
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    try:
        user_id = current_user.get("uid") if current_user else None
        user_tier = current_user.get("tier", "free") if current_user else "free"
        
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
        add_document("jobs", job_data)
        
        if os.getenv("USE_CELERY", "true").lower() == "true":
            generate_image_task.delay(
                job_id=job_id, 
                params=job_data["params"],
                user_id=user_id,
                user_tier=user_tier
            )
        else:
            # Fallback for local dev without Celery worker
            from backend.main import run_studio_task # type: ignore
            from fastapi import BackgroundTasks
            bt = BackgroundTasks()
            bt.add_task(
                run_studio_task, 
                job_id=job_id, 
                task_type="image", 
                params=job_data["params"],
                user_id=user_id,
                user_tier=user_tier
            )

        return {"status": "queued", "task_id": job_id, "message": "Image generation started."}

    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e), "status": "failed"})

@router.post("/generate_video")
async def gen_video(
    request: Request, 
    req: Query, 
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    try:
        user_id = current_user.get("uid") if current_user else None
        user_tier = current_user.get("tier", "free") if current_user else "free"

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
        add_document("jobs", job_data)
        
        if os.getenv("USE_CELERY", "true").lower() == "true":
            generate_video_task.delay(
                job_id=job_id, 
                params=job_data["params"],
                user_id=user_id,
                user_tier=user_tier
            )
        else:
             # Fallback
            from backend.main import run_studio_task # type: ignore
            from fastapi import BackgroundTasks
            bt = BackgroundTasks()
            bt.add_task(
                run_studio_task, 
                job_id=job_id, 
                task_type="video", 
                params=job_data["params"],
                user_id=user_id,
                user_tier=user_tier
            )

        return {"status": "queued", "task_id": job_id, "message": "Video synthesis started."}

    except Exception as e:
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
