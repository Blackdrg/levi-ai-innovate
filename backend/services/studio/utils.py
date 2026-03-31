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
    
    # 1. Credit Check
    cost = 1 if task_type == "image" else 2
    if not user_id.startswith("guest:"):
        try:
            use_credits(user_id, cost)
        except Exception as e:
            logger.error(f"Credit deduction failed: {e}")
            return {"status": "error", "error": "Insufficient credits or payment failure."}

    # 2. Prepare Job Data
    job_data = {
        "job_id": job_id,
        "type": task_type,
        "status": "queued",
        "user_id": user_id,
        "params": params,
        "created_at": datetime.utcnow()
    }

    # 3. Save to Firestore
    firestore_db.collection("jobs").document(job_id).set(job_data)

    # 4. Trigger Processing
    if os.getenv("USE_CELERY", "true").lower() == "true":
        task = generate_image_task if task_type == "image" else generate_video_task
        task.delay(
            job_id=job_id,
            params=params,
            user_id=user_id,
            user_tier=user_tier
        )
    else:
        # For local dev without Celery, we'd need BackgroundTasks from a request
        # but in orchestrator we can use asyncio.create_task or similar 
        # (though Celery is preferred for prod)
        # Phase 4: Safe Event Loop Handling for Local (Non-Celery) Execution
        from backend.services.studio.logic import run_studio_task
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(asyncio.to_thread(
                run_studio_task, job_id, task_type, params, user_id, user_tier
            ))
        except RuntimeError:
            # No running loop, use asyncio.run (standard for non-async callers)
            asyncio.run(asyncio.to_thread(
                run_studio_task, job_id, task_type, params, user_id, user_tier
            ))

    return {"status": "queued", "job_id": job_id, "message": f"{task_type.capitalize()} job initiated."}
