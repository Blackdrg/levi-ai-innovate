# pyright: reportMissingImports=false
"""
LEVI Celery Tasks v3.0
- Image + Video generation with S3 upload
- Credit refund on failure
- Push notifications
- Daily email dispatch
- Monthly credit reset
"""

import os
import uuid
import base64
import logging
import boto3  # type: ignore
from io import BytesIO
from typing import Any, Optional
from datetime import datetime
from celery import Celery  # type: ignore
from botocore.exceptions import BotoCoreError, ClientError  # type: ignore

try:
    from pywebpush import webpush, WebPushException  # type: ignore
    HAS_WEBPUSH = True
except ImportError:
    HAS_WEBPUSH = False


logger = logging.getLogger(__name__)

from backend.celery_app import celery_app # type: ignore


# ─────────────────────────────────────────────
# S3 Utilities
# ─────────────────────────────────────────────

def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )


def upload_to_s3(file_bytes: bytes, filename: str, content_type: str = "image/png") -> str:
    """Upload bytes to S3. Returns accessible URL."""
    bucket = os.getenv("AWS_S3_BUCKET", "levi-media")
    s3 = get_s3_client()

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


def upload_image_to_s3(image_bytes: bytes, user_id: Optional[int] = None) -> str:
    uid = str(user_id) if user_id else "anon"
    filename = f"images/{uid}/{uuid.uuid4().hex}.png"
    return upload_to_s3(image_bytes, filename, "image/png")


def upload_video_to_s3(video_bytes: bytes, user_id: Optional[int] = None) -> str:
    uid = str(user_id) if user_id else "anon"
    filename = f"videos/{uid}/{uuid.uuid4().hex}.mp4"
    return upload_to_s3(video_bytes, filename, "video/mp4")


try:
    from backend.firestore_db import db as firestore_db # type: ignore
except ImportError:
    from firestore_db import db as firestore_db # type: ignore

def _refund_credits(user_id: str, amount: int) -> None:
    """Refund credits to user after task failure in Firestore."""
    try:
        user_ref = firestore_db.collection("users").document(user_id)
        user_doc = user_ref.get()
        if user_doc.exists:
            current = user_doc.to_dict().get("credits", 0)
            user_ref.update({"credits": current + amount})
            logger.info(f"[Refund] Refunded {amount} credits to user {user_id}")
    except Exception as e:
        logger.error(f"[Refund] Failed: {e}")


# ─────────────────────────────────────────────
# Task 1: Image Generation
# ─────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def generate_image_task(
    self,
    quote: str,
    author: str,
    mood: str,
    user_id,
    user_tier: str = "free",
    style: str = "",
):
    from datetime import datetime
    import base64
    try:
        from backend.image_gen import generate_quote_image
    except ImportError:
        from image_gen import generate_quote_image

    logger.info(f"[ImageTask] Generating for user={user_id}, mood={mood}")

    try:
        if user_id and user_tier == "free":
            user_doc = firestore_db.collection("users").document(str(user_id)).get()
            if user_doc.exists:
                user_tier = user_doc.to_dict().get("tier", "free")

        result = generate_quote_image(
            quote=quote,
            author=author,
            mood=mood,
            user_tier=user_tier,
            style=style,
            upload_to_s3=bool(os.getenv("AWS_S3_BUCKET")),
            user_id=user_id,
        )

        image_url = None
        image_b64 = None

        if isinstance(result, dict):
            image_url = result.get("url")
            bio = result.get("bio")
            img_bytes = bio.read() if bio else b""
        else:
            img_bytes = result.getvalue() if hasattr(result, 'getvalue') else b""

        if img_bytes and not image_url and os.getenv("AWS_S3_BUCKET"):
            try:
                image_url = upload_image_to_s3(img_bytes, user_id)
            except Exception as upload_err:
                logger.warning(f"[ImageTask] S3 upload failed: {upload_err}")

        if not image_url and img_bytes:
            image_b64 = "data:image/png;base64," + base64.b64encode(img_bytes).decode()

        feed_ref = firestore_db.collection("feed_items")
        new_item_data = {
            "user_id": user_id,
            "text": quote,
            "author": author,
            "mood": mood,
            "image_url": image_url,
            "image_b64": image_b64 if not image_url else None,
            "likes": 0,
            "timestamp": datetime.utcnow()
        }
        _, doc_ref = feed_ref.add(new_item_data)

        return {
            "status": "completed",
            "url": image_url,
            "image_b64": image_b64,
            "id": doc_ref.id,
            "type": "image"
        }

    except Exception as e:
        logger.error(f"[ImageTask] Failed: {e}")
        if self.request.retries >= self.max_retries:
            if user_id:
                _refund_credits(str(user_id), 1)
            return {"status": "failed", "error": str(e)}
        raise self.retry(exc=e, countdown=10)

# ─────────────────────────────────────────────
# Task 2: Video Generation
# ─────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=1, default_retry_delay=30, time_limit=300)
def generate_video_task(
    self,
    quote: str,
    author: str,
    mood: str,
    user_id: Optional[str],
    user_tier: str = "free",
    aspect_ratio: str = "9:16",
):
    from datetime import datetime
    try:
        try:
            from backend.video_gen import generate_quote_video  # type: ignore
        except ImportError:
            from video_gen import generate_quote_video  # type: ignore

        logger.info(f"[VideoTask] Generating for user={user_id}, mood={mood}")

        video_bio = generate_quote_video(
            quote=quote,
            author=author,
            mood=mood,
            user_tier=user_tier,
            aspect_ratio=aspect_ratio,
        )
        video_bytes = video_bio.read()

        # Upload to S3
        video_url = None
        if os.getenv("AWS_S3_BUCKET"):
            try:
                video_url = upload_video_to_s3(video_bytes, user_id) # type: ignore
            except Exception as e:
                logger.warning(f"[VideoTask] S3 upload failed: {e}")

        # Save to Firestore Feed collection
        feed_ref = firestore_db.collection("feed_items")
        new_item_data = {
            "user_id": user_id,
            "text": quote,
            "author": author,
            "mood": mood,
            "video_url": video_url,
            "likes": 0,
            "timestamp": datetime.utcnow()
        }
        _, doc_ref = feed_ref.add(new_item_data)

        return {
            "status": "completed",
            "url": video_url,
            "id": doc_ref.id,
            "type": "video"
        }

    except Exception as e:
        logger.error(f"[VideoTask] Failed: {e}")

        if self.request.retries >= self.max_retries:
            if user_id:
                _refund_credits(str(user_id), 2)
            return {"status": "failed", "error": str(e)}

        raise self.retry(exc=e, countdown=30)


# ─────────────────────────────────────────────
# Task 3: Push Notifications
# ─────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_push_notification_task(
    self,
    subscription_id: str,
    endpoint: str,
    p256dh: str,
    auth: str,
    title: str,
    body: str,
):
    """Send Web Push notification to a specific subscription."""
    if not HAS_WEBPUSH:
        logger.warning("[Push] pywebpush not installed")
        return False

    private_key = os.getenv("VAPID_PRIVATE_KEY")
    admin_email = os.getenv("VAPID_ADMIN_EMAIL", "admin@levi-ai.create.app")

    if not private_key:
        logger.error("[Push] VAPID_PRIVATE_KEY not set")
        return False

    try:
        webpush(
            subscription_info={
                "endpoint": endpoint,
                "keys": {"p256dh": p256dh, "auth": auth}
            },
            data=f'{{"title": "{title}", "body": "{body}"}}',
            vapid_private_key=private_key,
            vapid_claims={"sub": f"mailto:{admin_email}"}
        )
        logger.info(f"[Push] Sent to subscription {subscription_id}")
        return True

    except Exception as ex:
        # Check for WebPushException
        if hasattr(ex, 'response') and ex.response is not None:  # type: ignore
            status = getattr(ex.response, 'status_code', None)  # type: ignore
            if status in (410, 404):
                # Subscription expired — remove from Firestore
                try:
                    firestore_db.collection("push_subscriptions").document(subscription_id).delete()
                    logger.info(f"[Push] Removed expired subscription {subscription_id}")
                except Exception:
                    pass
                return False

        logger.error(f"[Push] Failed: {ex}")
        raise self.retry(exc=ex, countdown=60)


# ─────────────────────────────────────────────
# Task 4: Daily Email Dispatch
# ─────────────────────────────────────────────

@celery_app.task
def send_daily_quote_email(user_email: str, user_id: str, liked_topics: list, last_mood: str = "philosophical"):
    """Send personalized daily quote email."""
    resend_key = os.getenv("RESEND_API_KEY")
    if not resend_key: return

    try:
        try:
            from backend.generation import generate_quote  # type: ignore
        except ImportError:
            from generation import generate_quote  # type: ignore

        topic = liked_topics[0] if liked_topics else "existence"
        quote = generate_quote(topic, mood=last_mood)

        import requests  # type: ignore
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {resend_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": "LEVI-AI <daily@levi-ai.create.app>",
                "to": [user_email],
                "subject": f"Your daily wisdom ✦ {topic.capitalize()}",
                "html": f"<div style='...'>{quote}</div>", # Simplified for brevity, original HTML could be kept
            },
            timeout=10
        )
        if resp.status_code in (200, 201):
            logger.info(f"[Email] Sent daily quote to {user_email}")
    except Exception as e:
        logger.error(f"[Email] Error for {user_email}: {e}")


@celery_app.task
def dispatch_daily_emails():
    """Dispatch daily emails + push notifications to all users via Firestore."""
    try:
        users_stream = firestore_db.collection("users").stream()
        dispatched = 0

        for user_doc in users_stream:
            try:
                user = user_doc.to_dict()
                u_id = user_doc.id
                topics = list(user.get("liked_topics", [])) or ["existence"]
                moods = list(user.get("mood_history", []))
                last_mood = moods[-1] if moods else "philosophical"

                # Email
                email = user.get("email")
                if email and user.get("is_verified", True):
                    send_daily_quote_email.delay(email, u_id, topics, last_mood)

                # Push
                subs_stream = firestore_db.collection("push_subscriptions").where("user_id", "==", u_id).stream()
                for sub_doc in subs_stream:
                    s = sub_doc.to_dict()
                    sid = sub_doc.id
                    send_push_notification_task.delay(
                        sid, s.get("endpoint"), s.get("p256dh"), s.get("auth"),
                        "LEVI Daily Wisdom ✦", "New wisdom awaits you today."
                    )
                dispatched += 1
            except Exception as e:
                logger.warning(f"[Dispatch] Failed for user {user_doc.id}: {e}")

        logger.info(f"[Dispatch] Sent to {dispatched} users")
        return {"status": "completed", "dispatched": dispatched}
    except Exception as e:
        logger.error(f"[Dispatch] Failed: {e}")
        return {"error": str(e)}


# ─────────────────────────────────────────────
# Task 5: Monthly Credit Reset
# ─────────────────────────────────────────────

@celery_app.task
def reset_monthly_credits():
    """Reset credits for paid users on the 1st of each month in Firestore."""
    try:
        from backend.payments import get_tier_credits  # type: ignore
        users_stream = firestore_db.collection("users").where("tier", "in", ["pro", "creator"]).stream()
        count = 0
        for user_doc in users_stream:
            tier = user_doc.to_dict().get("tier")
            user_doc.reference.update({"credits": get_tier_credits(tier or "free")})
            count += 1
        logger.info(f"[Credits] Reset {count} users")
        return {"status": "completed", "reset": count}
    except Exception as e:
        logger.error(f"[Credits] Reset failed: {e}")
        return {"error": str(e)}


# ─────────────────────────────────────────────
# Celery Beat Schedule
# ─────────────────────────────────────────────

from celery.schedules import crontab  # type: ignore

celery_app.conf.beat_schedule = {
    "daily-wisdom-dispatch": {
        "task": "backend.tasks.dispatch_daily_emails",
        "schedule": crontab(hour=8, minute=0),
    },
    "monthly-credit-reset": {
        "task": "backend.tasks.reset_monthly_credits",
        "schedule": crontab(day_of_month=1, hour=0, minute=5),
    },
}

# Import trainer schedule if available
try:
    from backend.trainer import TRAINING_BEAT_SCHEDULE  # type: ignore
    celery_app.conf.beat_schedule.update(TRAINING_BEAT_SCHEDULE)
except Exception:
    pass
