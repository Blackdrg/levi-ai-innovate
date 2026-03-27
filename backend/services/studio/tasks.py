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
