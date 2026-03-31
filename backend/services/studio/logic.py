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
    
    # Concurrency check
    slot_acquired = acquire_concurrency_slot(limit_key, max_concurrent)
    if not slot_acquired:
        logger.warning(f"Concurrency limit reached for {task_type} (Job: {job_id})")
    
    try:
        # 1. Update status to processing
        job_ref = firestore_db.collection("jobs").document(job_id)
        job_ref.update({"status": "processing", "started_at": datetime.utcnow()})
        
        # 2. Execute generation with Phase 8 Params
        if task_type == "image":
            result = generate_quote_image(
                quote=params["text"],
                author=params.get("author", "Unknown"),
                mood=params.get("mood", "neutral"),
                aspect_ratio=params.get("aspect_ratio", "1:1"),
                style=params.get("style", "cinematic"),
                negative_prompt=params.get("negative_prompt", ""),
                seed=params.get("seed"),
                user_tier=user_tier,
                user_id=user_id,
                custom_bg=params.get("custom_bg")
            )
        else:  # video
            result = generate_quote_video(
                quote=params["text"],
                author=params.get("author", "Unknown"),
                mood=params.get("mood", "neutral"),
                aspect_ratio=params.get("aspect_ratio", "9:16"),
                num_scenes=params.get("num_scenes", 3),
                user_tier=user_tier,
            )

        # 3. Handle Result & Storage
        if result and result.get("success"):
            data = result.get("data")
            final_url = None
            
            # If data is BytesIO (standard for engines)
            if isinstance(data, BytesIO):
                img_bytes = data.getvalue()
                from backend.s3_utils import upload_image_to_s3, upload_video_to_s3
                try:
                    if task_type == "image":
                        final_url = upload_image_to_s3(img_bytes, user_id)
                    else:
                        final_url = upload_video_to_s3(img_bytes, user_id)
                except Exception as e:
                    logger.error(f"Storage upload failed for {job_id}: {e}")
                
                # Base64 Fallback
                if not final_url:
                    b64_data = base64.b64encode(img_bytes).decode('utf-8')
                    mime_type = "image/png" if task_type == "image" else "video/mp4"
                    final_url = f"data:{mime_type};base64,{b64_data}"
            else:
                final_url = data

            # 4. Final Job Update
            update_payload = {
                "status": "completed",
                "completed_at": datetime.utcnow(),
                "url": final_url,
                "engine": result.get("engine", "sovereign_v6")
            }
            job_ref.update(update_payload)
            
            # 5. Gallery / Feed Indexing (Phase 9 Readiness)
            # Standardize for both types now
            feed_payload = {
                "user_id": user_id,
                "text": params["text"],
                "author": params.get("author", "Unknown"),
                "type": task_type,
                "aspect_ratio": params.get("aspect_ratio", "1:1"),
                "style": params.get("style", "default"),
                "timestamp": datetime.utcnow(),
                "job_id": job_id,
                "likes": 0
            }
            if isinstance(final_url, str):
                if final_url.startswith("data:"):
                    feed_payload[f"{task_type}_b64"] = final_url
                else:
                    feed_payload[f"{task_type}_url"] = final_url
            
            add_document("feed_items", feed_payload)
            
            return {"status": "success", "job_id": job_id, "url": final_url}
        else:
            error_msg = str(result.get("error")) if result else "Generation failed"
            job_ref.update({
                "status": "failed",
                "error": error_msg,
                "completed_at": datetime.utcnow()
            })
            return {"status": "failed", "job_id": job_id, "error": error_msg}

    except Exception as e:
        logger.critical(f"Studio Job {job_id} FAILURE: {e}")
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
