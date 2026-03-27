from backend.celery_app import celery_app # type: ignore
from backend.image_gen import generate_quote_image # type: ignore
from backend.video_gen import generate_quote_video # type: ignore
from backend.firestore_db import db as firestore_db, add_document # type: ignore
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def generate_image_task(self, job_id, params, user_id, user_tier):
    """Celery task to generate an image for a quote."""
    try:
        # Update job status to processing
        job_ref = firestore_db.collection("jobs").document(job_id)
        job_ref.update({"status": "processing", "started_at": datetime.utcnow()})
        
        # Execute generation
        result = generate_quote_image(
            params["text"],
            author=params.get("author", "Unknown"),
            mood=params.get("mood", "neutral"),
            user_tier=user_tier,
            user_id=user_id,
            custom_bg=params.get("custom_bg")
        )

        # Handle result
        if result and result.get("success"):
            data_url = result.get("data")
            job_ref.update({
                "status": "completed",
                "url": data_url,
                "completed_at": datetime.utcnow(),
                "engine": result.get("engine")
            })
            
            # Add to feed
            add_document("feed_items", {
                "user_id": user_id,
                "text": params["text"],
                "author": params.get("author", "Unknown"),
                "url": data_url,
                "type": "image",
                "timestamp": datetime.utcnow(),
                "job_id": job_id
            })
            return {"status": "success", "job_id": job_id, "url": data_url}
        else:
            error_msg = result.get("error") if result else "Unknown generation failure"
            job_ref.update({
                "status": "failed",
                "error": error_msg,
                "completed_at": datetime.utcnow()
            })
            return {"status": "failed", "job_id": job_id, "error": error_msg}

    except Exception as e:
        logger.error(f"Task generate_image_task failed for {job_id}: {e}")
        try:
            self.retry(exc=e, countdown=60) # Retry after 1 minute
        except Exception:
             job_ref.update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.utcnow()
            })
        return {"status": "failed", "job_id": job_id, "error": str(e)}

@celery_app.task(bind=True, max_retries=2)
def generate_video_task(self, job_id, params, user_id, user_tier):
    """Celery task to generate a video for a quote."""
    try:
        job_ref = firestore_db.collection("jobs").document(job_id)
        job_ref.update({"status": "processing", "started_at": datetime.utcnow()})
        
        result = generate_quote_video(
            params["text"],
            author=params.get("author", "Unknown"),
            mood=params.get("mood", "neutral"),
            user_tier=user_tier,
            user_id=user_id,
        )

        if result and result.get("success"):
            data_url = result.get("data")
            job_ref.update({
                "status": "completed",
                "url": data_url,
                "completed_at": datetime.utcnow(),
                "engine": result.get("engine")
            })
            return {"status": "success", "job_id": job_id, "url": data_url}
        else:
            error_msg = result.get("error") if result else "Unknown video synthesis failure"
            job_ref.update({
                "status": "failed",
                "error": error_msg,
                "completed_at": datetime.utcnow()
            })
            return {"status": "failed", "job_id": job_id, "error": error_msg}

    except Exception as e:
        logger.error(f"Task generate_video_task failed for {job_id}: {e}")
        try:
            self.retry(exc=e, countdown=120)
        except Exception:
            job_ref.update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.utcnow()
            })
        return {"status": "failed", "job_id": job_id, "error": str(e)}
