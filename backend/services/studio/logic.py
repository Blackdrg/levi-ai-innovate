import logging
import base64
from datetime import datetime
from io import BytesIO
from typing import Optional, Dict, Any

from backend.firestore_db import db as firestore_db, add_document
from backend.image_gen import generate_quote_image
from backend.video_gen import generate_quote_video
from backend.s3_utils import upload_image_to_s3, upload_video_to_s3
from backend.redis_client import acquire_concurrency_slot, release_concurrency_slot

logger = logging.getLogger(__name__)

def run_studio_task(job_id: str, task_type: str, params: Dict[str, Any], user_id: Optional[str] = None, user_tier: str = "free"):
    """
    Core logic for studio tasks (image/video generation).
    Used by both Celery workers and synchronous fallback paths.
    """
    limit_key = f"concurrency:{task_type}_gen"
    max_concurrent = 2 if task_type == "video" else 5
    
    # Concurrency check (best effort for sync path, mandatory for worker)
    slot_acquired = acquire_concurrency_slot(limit_key, max_concurrent)
    if not slot_acquired:
        logger.warning(f"Concurrency limit reached for {task_type} (Job: {job_id})")
        # In sync path, we might just proceed or fail. For now, we proceed but log.
    
    try:
        # 1. Update status to processing
        job_ref = firestore_db.collection("jobs").document(job_id)
        job_ref.update({"status": "processing", "started_at": datetime.utcnow()})
        
        # 2. Execute generation
        if task_type == "image":
            result = generate_quote_image(
                params["text"],
                author=params.get("author", "Unknown"),
                mood=params.get("mood", "neutral"),
                user_tier=user_tier,
                user_id=user_id,
                custom_bg=params.get("custom_bg")
            )
        else:  # video
            result = generate_quote_video(
                params["text"],
                author=params.get("author", "Unknown"),
                mood=params.get("mood", "neutral"),
                user_tier=user_tier,
            )

        # 3. Handle Result & Storage
        if result and result.get("success"):
            data = result.get("data")
            final_url = None
            
            # If data is BytesIO (not yet uploaded to S3 by the engine itself)
            if isinstance(data, BytesIO):
                img_bytes = data.getvalue()
                
                # Try S3 Upload
                try:
                    if task_type == "image":
                        final_url = upload_image_to_s3(img_bytes, user_id)
                    else:
                        final_url = upload_video_to_s3(img_bytes, user_id)
                except Exception as e:
                    logger.error(f"S3 Upload failed for {job_id}: {e}")
                
                # Fallback to Base64 if S3 failed or not configured
                if not final_url:
                    logger.info(f"Falling back to Base64 for {job_id}")
                    b64_data = base64.b64encode(img_bytes).decode('utf-8')
                    mime_type = "image/png" if task_type == "image" else "video/mp4"
                    final_url = f"data:{mime_type};base64,{b64_data}"
            else:
                # Already a URL (e.g. from Together AI direct or already uploaded)
                final_url = data

            # 4. Final Updates
            job_ref.update({
                "status": "completed",
                "url": final_url,
                "completed_at": datetime.utcnow(),
                "engine": result.get("engine")
            })
            
            # Add to feed (images only for now)
            if task_type == "image":
                add_document("feed_items", {
                    "user_id": user_id,
                    "text": params["text"],
                    "author": params.get("author", "Unknown"),
                    "image_url": final_url if not final_url.startswith("data:") else None,
                    "image_b64": final_url if final_url.startswith("data:") else None,
                    "type": "image",
                    "timestamp": datetime.utcnow(),
                    "job_id": job_id,
                    "likes": 0
                })
            
            return {"status": "success", "job_id": job_id, "url": final_url}
        else:
            error_msg = result.get("error") if result else "Generation failed without error message"
            job_ref.update({
                "status": "failed",
                "error": error_msg,
                "completed_at": datetime.utcnow()
            })
            return {"status": "failed", "job_id": job_id, "error": error_msg}

    except Exception as e:
        logger.critical(f"🚨 ALERT: Studio Job {job_id} CRITICAL FAILURE: {e}")
        try:
           firestore_db.collection("jobs").document(job_id).update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.utcnow()
            })
        except: pass
        return {"status": "failed", "job_id": job_id, "error": str(e)}
    finally:
        if slot_acquired:
            release_concurrency_slot(limit_key)
