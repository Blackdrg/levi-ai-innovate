"""
backend/jobs/video_job.py

Cloud Run Job Entrypoint for High-Intensity Video Generation.
Triggered by Cloud Tasks or direct gcloud command.
"""

import os
import sys
import logging
import asyncio

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.video_gen import generate_quote_video
from backend.db.firestore_db import db as firestore_db
from backend.db.gcs_utils import upload_video_to_gcs

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

async def run_video_job():
    """
    Main job logic:
    1. Parse job_id from cloud environment.
    2. Fetch job configuration from Firestore.
    3. Execute video generation.
    4. Upload to GCS.
    5. Update Firestore status.
    """
    job_id = os.getenv("JOB_ID")
    if not job_id:
        # Check command line args
        if len(sys.argv) > 1:
            job_id = sys.argv[1]
        else:
            logger.error("No JOB_ID provided. Exiting.")
            sys.exit(1)

    logger.info(f"🚀 Starting Video Job: {job_id}")

    # 1. Fetch Job from Firestore
    job_ref = firestore_db.collection("jobs").document(job_id)
    job_doc = job_ref.get()
    
    if not job_doc.exists:
        logger.error(f"Job {job_id} not found in Firestore.")
        sys.exit(1)

    job_data = job_doc.to_dict()
    if job_data.get("status") == "completed":
        logger.info(f"Job {job_id} already completed. skipping.")
        return

    # 2. Update status to 'processing'
    job_ref.update({"status": "processing", "started_at": firestore_db.FieldValue.serverTimestamp()})

    try:
        # 3. Generate Video
        # We assume generate_quote_video handles the heavy lifting
        quote = job_data.get("quote", "The universe is a dream.")
        author = job_data.get("author", "Anonymous")
        mood = job_data.get("mood", "philosophical")
        style = job_data.get("style", "cinematic")
        user_id = job_data.get("user_id")

        logger.info(f"Generating video for: {quote[:40]}...")
        
        # Note: generate_quote_video currently returns BytesIO in our codebase
        # or it might have changed to return path/dict depending on latest edits.
        # We'll use the result and upload to GCS.
        video_result = await asyncio.to_thread(
            generate_quote_video,
            quote=quote,
            author=author,
            mood=mood,
            style=style
        )

        if not video_result:
            raise Exception("Video generation returned no result.")

        # 4. Upload to GCS
        # video_result is typically a BytesIO from video_gen.py
        video_bytes = video_result.getvalue() if hasattr(video_result, "getvalue") else video_result
        
        logger.info(f"Uploading {len(video_bytes)} bytes to GCS...")
        public_url = upload_video_to_gcs(video_bytes, user_id=user_id, expires_in=604800) # 7 days signature

        if not public_url:
            raise Exception("GCS upload failed.")

        # 5. Finalize Job
        job_ref.update({
            "status": "completed",
            "result_url": public_url,
            "completed_at": firestore_db.FieldValue.serverTimestamp(),
            "progress": 100
        })
        
        logger.info(f"✅ Video Job {job_id} completed successfully! URL: {public_url}")

    except Exception as e:
        logger.error(f"❌ Video Job {job_id} failed: {e}", exc_info=True)
        job_ref.update({
            "status": "failed",
            "error": str(e),
            "completed_at": firestore_db.FieldValue.serverTimestamp()
        })
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_video_job())
