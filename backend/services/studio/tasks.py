from backend.celery_app import celery_app # type: ignore
from backend.image_gen import generate_quote_image # type: ignore
from backend.video_gen import generate_quote_video # type: ignore
from backend.firestore_db import db as firestore_db, add_document # type: ignore
from backend.redis_client import acquire_concurrency_slot, release_concurrency_slot # type: ignore
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=5, default_retry_delay=30)
def generate_image_task(self, job_id, params, user_id, user_tier):
    """Celery task to generate an image for a quote with global concurrency control."""
    limit_key = "concurrency:image_gen"
    max_concurrent = 5
    
    if not acquire_concurrency_slot(limit_key, max_concurrent):
        logger.info(f"Image generation limit reached for {job_id}, retrying...")
        raise self.retry(countdown=10) # Quick retry if limit reached
    
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
        # Exponential backoff: 30s, 60s, 120s, 240s, 480s
        countdown = 30 * (2 ** self.request.retries)
        try:
            self.retry(exc=e, countdown=countdown)
        except Exception:
             job_ref.update({
                "status": "failed",
                "error": f"Max retries exceeded: {str(e)}",
                "completed_at": datetime.utcnow()
            })
        return {"status": "failed", "job_id": job_id, "error": str(e)}
    finally:
        release_concurrency_slot(limit_key)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_video_task(self, job_id, params, user_id, user_tier):
    """Celery task to generate a video for a quote with strict concurrency control."""
    limit_key = "concurrency:video_gen"
    max_concurrent = 2
    
    if not acquire_concurrency_slot(limit_key, max_concurrent):
        logger.info(f"Video synthesis limit reached for {job_id}, retrying...")
        raise self.retry(countdown=30)
    
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
        countdown = 60 * (2 ** self.request.retries)
        try:
            self.retry(exc=e, countdown=countdown)
        except Exception:
            job_ref.update({
                "status": "failed",
                "error": f"Max retries reached: {str(e)}",
                "completed_at": datetime.utcnow()
            })
        return {"status": "failed", "job_id": job_id, "error": str(e)}
    finally:
        release_concurrency_slot(limit_key)
