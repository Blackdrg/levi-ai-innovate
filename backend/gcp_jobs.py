import os
import logging
from typing import Optional, Dict, Any
from google.cloud import run_v2 # type: ignore

logger = logging.getLogger(__name__)

def trigger_video_job(job_id: str) -> bool:
    """
    Triggers a Cloud Run Job ('levi-video-job') using the Google Cloud Run API.
    Passes the JOB_ID as an environment variable override.
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    region = os.getenv("GCP_REGION", "us-central1")
    
    if not project_id:
        logger.error("GOOGLE_CLOUD_PROJECT not set. Cannot trigger job.")
        return False

    try:
        client = run_v2.JobsClient()
        job_name = f"projects/{project_id}/locations/{region}/jobs/levi-video-job"
        
        # Create the execution request with overrides
        request = run_v2.RunJobRequest(
            name=job_name,
            overrides=run_v2.RunJobRequest.Overrides(
                container_overrides=[
                    run_v2.RunJobRequest.Overrides.ContainerOverride(
                        env=[
                            run_v2.RunJobRequest.Overrides.EnvVar(
                                name="JOB_ID",
                                value=job_id
                            )
                        ]
                    )
                ]
            )
        )
        
        operation = client.run_job(request=request)
        logger.info(f"Triggered Cloud Run Job execution for {job_id}. Operation: {operation.operation.name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to trigger Cloud Run Job for {job_id}: {e}")
        return False

def enqueue_video_task(job_data: Dict[str, Any]) -> Optional[str]:
    """
    Phase 50: Cloud Tasks Integration.
    Instead of running heavy logic in Celery, we queue a 'start-job' task 
    or directly trigger the Cloud Run Job.
    
    Here we create the record in Firestore first.
    """
    from backend.db.firestore_db import db as firestore_db
    
    # 1. Create Job Doc in Firestore
    job_id = f"job_{os.urandom(4).hex()}"
    job_data.update({
        "status": "queued",
        "created_at": firestore_db.FieldValue.serverTimestamp(),
        "type": "video"
    })
    
    firestore_db.collection("jobs").document(job_id).set(job_data)
    
    # 2. Trigger the Job immediately
    # (In a more complex setup, we'd use Cloud Tasks to rate-limit these triggers)
    success = trigger_video_job(job_id)
    
    if success:
        return job_id
    return None
