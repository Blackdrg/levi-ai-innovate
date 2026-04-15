from backend.celery_app import celery_app # type: ignore
from backend.services.studio.logic import run_studio_task # type: ignore
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=5, default_retry_delay=30)
def generate_image_task(self, job_id, params, user_id, user_tier):
    """Celery task to generate an image for a quote with global concurrency control."""
    try:
        return run_studio_task(
            job_id=job_id,
            task_type="image",
            params=params,
            user_id=user_id,
            user_tier=user_tier
        )
    except Exception as e:
        logger.error(f"Task generate_image_task failed for {job_id}: {e}")
        countdown = 30 * (2 ** self.request.retries)
        raise self.retry(exc=e, countdown=countdown)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_video_task(self, job_id, params, user_id, user_tier):
    """Celery task to generate a video for a quote with strict concurrency control."""
    try:
        return run_studio_task(
            job_id=job_id,
            task_type="video",
            params=params,
            user_id=user_id,
            user_tier=user_tier
        )
    except Exception as e:
        logger.error(f"Task generate_video_task failed for {job_id}: {e}")
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=e, countdown=countdown)

@celery_app.task(name="backend.services.studio.tasks.cleanup_stuck_jobs")
def cleanup_stuck_jobs():
    """
    Sovereign v16.1 Hardening: Stuck Job Recon.
    Finds jobs in 'processing' status for more than 1 hour and mark them as failed.
    Prevents concurrency slot leaking and phantom mission indicators.
    """
    from datetime import datetime, timedelta
    from backend.db.firestore_db import db as firestore_db
    
    logger.info("🧹 [Studio-Recon] Starting stuck job cleanup...")
    
    # 1 hour threshold for long-running generative tasks
    threshold = datetime.utcnow() - timedelta(hours=1)
    
    try:
        stuck_jobs = firestore_db.collection("jobs")\
            .where("status", "==", "processing")\
            .where("started_at", "<", threshold)\
            .stream()
        
        count = 0
        for job in stuck_jobs:
            job.reference.update({
                "status": "failed",
                "error": "Job timed out or worker abandoned task (v16.1 Recon)",
                "completed_at": datetime.utcnow()
            })
            logger.warning(f"⚠️ [Studio-Recon] Cleaned up stuck job: {job.id}")
            count += 1
        
        if count > 0:
            logger.info(f"✅ [Studio-Recon] Successfully reconciled {count} stuck jobs.")
        else:
            logger.info("[Studio-Recon] System hygiene nominal. No stuck jobs found.")
            
        return count
    except Exception as e:
        logger.error(f"❌ [Studio-Recon] Reconnaissance failed: {e}")
        return 0

