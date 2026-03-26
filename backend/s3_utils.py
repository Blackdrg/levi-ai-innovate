import os
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def get_s3_client():
    try:
        import boto3 # type: ignore
        return boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )
    except ImportError:
        logger.warning("boto3 not installed. S3 upload unavailable.")
        return None

def upload_to_s3(file_bytes: bytes, filename: str, content_type: str) -> Optional[str]:
    """Upload bytes to S3. Returns accessible URL."""
    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        return None
        
    s3 = get_s3_client()
    if not s3:
        return None

    try:
        s3.put_object(
            Bucket=bucket,
            Key=filename,
            Body=file_bytes,
            ContentType=content_type,
        )

        cloudfront = os.getenv("CLOUDFRONT_DOMAIN")
        if cloudfront:
            return f"https://{cloudfront}/{filename}"

        # Pre-signed URL (7 days)
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": filename},
            ExpiresIn=604800,
        )
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        return None

def upload_image_to_s3(image_bytes: bytes, user_id: Optional[str] = None) -> Optional[str]:
    uid = str(user_id) if user_id else "anon"
    filename = f"images/{uid}/{uuid.uuid4().hex}.png"
    return upload_to_s3(image_bytes, filename, "image/png")

def upload_video_to_s3(video_bytes: bytes, user_id: Optional[str] = None) -> Optional[str]:
    uid = str(user_id) if user_id else "anon"
    filename = f"videos/{uid}/{uuid.uuid4().hex}.mp4"
    return upload_to_s3(video_bytes, filename, "video/mp4")
