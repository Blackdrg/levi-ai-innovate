import uuid
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

from backend.firestore_db import db as firestore_db
from backend.services.studio.tasks import generate_image_task, generate_video_task
from backend.payments import use_credits

logger = logging.getLogger(__name__)

def create_studio_job(
    task_type: str,
    params: Dict[str, Any],
    user_id: str,
    user_tier: str = "free"
) -> Dict[str, Any]:
    """Universal helper to create a studio generation job (Image or Video)."""
    
    prefix = "job_" if task_type == "image" else "vjob_"
    job_id = f"{prefix}{uuid.uuid4().hex[:12]}"
    
    # ── Phase 8: Parameter Normalization ──
    # Clean and validate basic params
    normalized_params = params.copy()
    if task_type == "image":
        normalized_params.setdefault("aspect_ratio", "1:1")
        normalized_params.setdefault("style", "cinematic")
    else:
        normalized_params.setdefault("aspect_ratio", "9:16")
        normalized_params.setdefault("motion_bucket_id", 127)

    # 1. Credit Check
    cost = 1 if task_type == "image" else 2
    # Premium tiers may have discounted or unlimited generation (uncomment if logic exists)
    # if user_tier in ("pro", "creator"): cost = 0

    if not user_id.startswith("guest:"):
        try:
            use_credits(user_id, cost)
        except Exception as e:
            logger.error(f"Credit deduction failed: {e}")
            return {"status": "error", "error": f"Insufficient credits ({cost} required)."}

    # 2. Prepare Job Data
    job_data = {
        "job_id": job_id,
        "type": task_type,
        "status": "queued",
        "user_id": user_id,
        "user_tier": user_tier,
        "params": normalized_params,
        "metadata": {
            "engine": "sovereign_v6",
            "version": "1.0.0-hardened"
        },
        "created_at": datetime.utcnow()
    }

    # 3. Save to Firestore
    firestore_db.collection("jobs").document(job_id).set(job_data)

    # 4. Trigger Processing
    if os.getenv("USE_CELERY", "true").lower() == "true":
        task = generate_image_task if task_type == "image" else generate_video_task
        task.delay(
            job_id=job_id,
            params=normalized_params,
            user_id=user_id,
            user_tier=user_tier
        )
    else:
        from backend.services.studio.logic import run_studio_task
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(asyncio.to_thread(
                run_studio_task, job_id, task_type, normalized_params, user_id, user_tier
            ))
        except RuntimeError:
            asyncio.run(asyncio.to_thread(
                run_studio_task, job_id, task_type, normalized_params, user_id, user_tier
            ))

    return {"status": "queued", "job_id": job_id, "message": f"{task_type.capitalize()} job initiated."}
