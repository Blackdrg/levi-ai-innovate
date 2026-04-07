# backend/services/studio/image_logic.py
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from backend.db.firestore_db import db as firestore_db
from backend.engines.studio.sd_logic import generate_image_logic
from backend.utils.logger import get_logger

logger = get_logger("studio_image")

async def process_image_generation(job_id: str, payload: Dict[str, Any]):
    """Processes an image generation job from the queue."""
    user_id = payload.get("user_id")
    prompt = payload.get("prompt")
    style = payload.get("style", "default")
    
    job_ref = firestore_db.collection("jobs").document(job_id)
    await asyncio.to_thread(job_ref.update, {"status": "processing", "started_at": datetime.now(timezone.utc)})
    
    try:
        # Call the underlying engine
        image_buf = await asyncio.to_thread(generate_image_logic, prompt, style=style)
        
        if not image_buf:
            raise Exception("Image engine returned no data.")
            
        # 1. Upload to Storage (Google Cloud Storage / AWS S3)
        # For now, we simulate storage with a local path or placeholder
        image_url = f"https://storage.googleapis.com/levi-assets/images/{job_id}.png"
        
        # 2. Update Firestore
        update_data = {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc),
            "result_url": image_url,
            "metadata": {"style": style, "prompt": prompt}
        }
        await asyncio.to_thread(job_ref.update, update_data)
        
        # 3. Add to Gallery
        gallery_ref = firestore_db.collection("gallery").document(job_id)
        await asyncio.to_thread(gallery_ref.set, {
            "user_id": user_id,
            "url": image_url,
            "type": "image",
            "created_at": datetime.now(timezone.utc),
            "prompt": prompt,
            "is_public": payload.get("is_public", True)
        })
        
        logger.info(f"Image job {job_id} completed successfully.")
        
    except Exception as e:
        logger.error(f"Image job {job_id} failed: {e}")
        await asyncio.to_thread(job_ref.update, {
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now(timezone.utc)
        })
