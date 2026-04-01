import os
import uuid
import logging
from typing import Optional
from google.cloud import storage # type: ignore

logger = logging.getLogger(__name__)

def get_gcs_client():
    try:
        return storage.Client()
    except Exception as e:
        logger.warning(f"Could not initialize GCS client: {e}")
        return None

def upload_to_gcs(file_bytes: bytes, filename: str, content_type: str, expires_in: int = 3600) -> Optional[str]:
    """Upload bytes to GCS. Returns accessible signed URL."""
    bucket_name = os.getenv("GCP_STORAGE_BUCKET")
    if not bucket_name:
        # Fallback to project-based naming from setup script
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if project_id:
            bucket_name = f"levi-media-{project_id}"
        else:
            return None
        
    client = get_gcs_client()
    if not client:
        return None

    try:
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.upload_from_string(file_bytes, content_type=content_type)

        # Generate a signed URL for secure access
        url = blob.generate_signed_url(
            version="v4",
            expiration=expires_in,
            method="GET",
        )
        return url
    except Exception as e:
        logger.error(f"GCS upload failed: {e}")
        return None

def upload_image_to_gcs(image_bytes: bytes, user_id: Optional[str] = None, expires_in: int = 86400) -> Optional[str]:
    uid = str(user_id) if user_id else "anon"
    filename = f"images/{uid}/{uuid.uuid4().hex}.png"
    return upload_to_gcs(image_bytes, filename, "image/png", expires_in=expires_in)

def upload_video_to_gcs(video_bytes: bytes, user_id: Optional[str] = None, expires_in: int = 86400) -> Optional[str]:
    uid = str(user_id) if user_id else "anon"
    filename = f"videos/{uid}/{uuid.uuid4().hex}.mp4"
    return upload_to_gcs(video_bytes, filename, "video/mp4", expires_in=expires_in)
