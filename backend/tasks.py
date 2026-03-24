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
from celery import Celery  # type: ignore
from botocore.exceptions import BotoCoreError, ClientError  # type: ignore

try:
    from pywebpush import webpush, WebPushException  # type: ignore
    HAS_WEBPUSH = True
except ImportError:
    HAS_WEBPUSH = False

try:
    from backend.db import SessionLocal  # type: ignore
    from backend.models import FeedItem, Users, PushSubscription  # type: ignore
except ImportError:
    from db import SessionLocal  # type: ignore
    from models import FeedItem, Users, PushSubscription  # type: ignore

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Celery Setup
# ─────────────────────────────────────────────

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
celery_app = Celery("levi", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    result_expires=3600,
    task_acks_late=True,           # Ack after task completes
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,   # One task at a time per worker
)


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


def _refund_credits(user_id: int, amount: int) -> None:
    """Refund credits to user after task failure."""
    try:
        db = SessionLocal()
        user = db.query(Users).filter(Users.id == user_id).first()
        if user:
            user.credits = (user.credits or 0) + amount
            db.commit()
            logger.info(f"[Refund] Refunded {amount} credits to user {user_id}")
        db.close()
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
    user_id: Optional[int],
    user_tier: str = "free",
    style: str = "",
):
    """
    Background task: Generate image via Together AI + upload to S3.
    Returns {"status": "done", "url": ..., "id": ..., "type": ...}
    """
    db = SessionLocal()
    try:
        try:
            from backend.image_gen import generate_quote_image  # type: ignore
        except ImportError:
            from image_gen import generate_quote_image  # type: ignore

        logger.info(f"[ImageTask] Generating for user={user_id}, mood={mood}, style={style}")

        # Get user tier from DB if not provided correctly
        if user_id and user_tier == "free":
            user = db.query(Users).filter(Users.id == user_id).first()
            if user:
                user_tier = user.tier or "free"

        result = generate_quote_image(
            quote=quote,
            author=author,
            mood=mood,
            user_tier=user_tier,
            style=style,
            upload_to_s3=bool(os.getenv("AWS_S3_BUCKET")),
            user_id=user_id,
        )

        # Handle S3 upload result vs BytesIO
        image_url = None
        image_b64 = None

        if isinstance(result, dict):
            image_url = result.get("url")
            bio = result.get("bio")
            if bio:
                bio.seek(0)
                img_bytes = bio.read()
            else:
                img_bytes = b""
        else:
            # BytesIO
            img_bytes = result.getvalue() if hasattr(result, 'getvalue') else b""

        # Upload to S3 if not already done
        if img_bytes and not image_url and os.getenv("AWS_S3_BUCKET"):
            try:
                image_url = upload_image_to_s3(img_bytes, user_id)
            except Exception as e:
                logger.warning(f"[ImageTask] S3 upload failed: {e}")

        # Base64 fallback
        if not image_url and img_bytes:
            image_b64 = "data:image/png;base64," + base64.b64encode(img_bytes).decode()

        # Save to FeedItem
        new_item = FeedItem(
            user_id=user_id,
            text=quote,
            author=author,
            mood=mood,
            image_url=image_url,
            image_b64=image_b64 if not image_url else None,
            likes=0,
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)

        return {
            "status": "done",
            "url": image_url or image_b64,
            "id": new_item.id,
            "type": "s3" if image_url else "base64",
        }

    except Exception as e:
        db.close()
        logger.error(f"[ImageTask] Failed (attempt {self.request.retries + 1}): {e}")

        if self.request.retries >= self.max_retries:
            if user_id:
                _refund_credits(user_id, 1)
            return {"status": "failed", "error": str(e)}

        raise self.retry(exc=e, countdown=min(10 * (self.request.retries + 1), 60))
    finally:
        try:
            db.close()
        except Exception:
            pass


# ─────────────────────────────────────────────
# Task 2: Video Generation
# ─────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=1, default_retry_delay=30, time_limit=300)
def generate_video_task(
    self,
    quote: str,
    author: str,
    mood: str,
    user_id: Optional[int],
    user_tier: str = "free",
    aspect_ratio: str = "9:16",
):
    """
    Background task: Generate video + upload to S3.
    """
    db = SessionLocal()
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
                video_url = upload_video_to_s3(video_bytes, user_id)
            except Exception as e:
                logger.warning(f"[VideoTask] S3 upload failed: {e}")

        # Save to FeedItem
        new_item = FeedItem(
            user_id=user_id,
            text=quote,
            author=author,
            mood=mood,
            video_url=video_url,
            likes=0,
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)

        return {
            "status": "done",
            "url": video_url,
            "id": new_item.id,
        }

    except Exception as e:
        logger.error(f"[VideoTask] Failed: {e}")
        db.rollback()

        if self.request.retries >= self.max_retries:
            if user_id:
                _refund_credits(user_id, 2)
            return {"status": "failed", "error": str(e)}

        raise self.retry(exc=e, countdown=30)
    finally:
        try:
            db.close()
        except Exception:
            pass


# ─────────────────────────────────────────────
# Task 3: Push Notifications
# ─────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_push_notification_task(
    self,
    subscription_id: int,
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
                # Subscription expired — remove it
                try:
                    db = SessionLocal()
                    db.query(PushSubscription).filter(
                        PushSubscription.id == subscription_id
                    ).delete()
                    db.commit()
                    db.close()
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
def send_daily_quote_email(user_email: str, user_id: int, liked_topics: list, last_mood: str = "philosophical"):
    """Send personalized daily quote email."""
    resend_key = os.getenv("RESEND_API_KEY")
    if not resend_key:
        return

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
                "from": "LEVI AI <daily@levi-ai.create.app>",
                "to": [user_email],
                "subject": f"Your daily wisdom ✦ {topic.capitalize()}",
                "html": f"""
<div style="font-family: 'Georgia', serif; max-width: 600px; margin: auto;
     padding: 48px 40px; background: #131317; color: #e5e1e7;
     border-radius: 16px;">
  <h2 style="color: #f2ca50; font-style: italic; font-size: 28px;
      margin-bottom: 8px; letter-spacing: -0.5px;">LEVI AI</h2>
  <p style="color: #71717a; font-size: 11px; letter-spacing: 0.2em;
     text-transform: uppercase; margin-bottom: 40px;">Daily Wisdom</p>

  <blockquote style="font-style: italic; font-size: 22px; line-height: 1.7;
      border-left: 3px solid #f2ca50; padding-left: 20px;
      margin: 0 0 32px 0; color: #e5e1e7;">
    {quote}
  </blockquote>

  <div style="text-align: center; margin-top: 40px;">
    <a href="{os.getenv('FRONTEND_URL', 'https://levi-ai.create.app')}/studio.html"
       style="background: linear-gradient(135deg, #f2ca50, #d4af37);
              color: #3c2f00; padding: 14px 32px; border-radius: 100px;
              text-decoration: none; font-weight: bold; font-size: 13px;
              letter-spacing: 0.1em; text-transform: uppercase;">
      Open Studio
    </a>
  </div>

  <hr style="border: 0; border-top: 1px solid #2a292e; margin: 40px 0;">
  <p style="color: #52525b; font-size: 11px; text-align: center;">
    Sent by LEVI AI · <a href="#" style="color: #52525b;">Unsubscribe</a>
  </p>
</div>
                """,
            },
            timeout=10
        )
        if resp.status_code in (200, 201):
            logger.info(f"[Email] Sent daily quote to {user_email}")
        else:
            logger.warning(f"[Email] Failed for {user_email}: {resp.status_code}")
    except Exception as e:
        logger.error(f"[Email] Error for {user_email}: {e}")


@celery_app.task
def dispatch_daily_emails():
    """Dispatch daily emails + push notifications to all users."""
    try:
        db = SessionLocal()
        users = db.query(Users).all()
        dispatched = 0

        for user in users:
            try:
                topics = list(user.liked_topics or []) or ["existence"]
                moods = list(user.mood_history or [])
                last_mood = moods[-1] if moods else "philosophical"

                # Email
                if user.email and user.is_verified:
                    send_daily_quote_email.delay(
                        user.email, user.id, topics, last_mood
                    )

                # Push
                subs = db.query(PushSubscription).filter(
                    PushSubscription.user_id == user.id
                ).all()

                if subs:
                    try:
                        try:
                            from backend.generation import generate_quote  # type: ignore
                        except ImportError:
                            from generation import generate_quote  # type: ignore
                        quote = generate_quote(topics[0] if topics else "life", last_mood)
                    except Exception:
                        quote = "New wisdom awaits you today."

                    for s in subs:
                        send_push_notification_task.delay(
                            s.id, s.endpoint, s.p256dh, s.auth,
                            "LEVI Daily Wisdom ✦", quote[:100]
                        )

                dispatched += 1
            except Exception as e:
                logger.warning(f"[Dispatch] Failed for user {user.id}: {e}")

        db.close()
        logger.info(f"[Dispatch] Sent to {dispatched} users")
        return {"dispatched": dispatched}

    except Exception as e:
        logger.error(f"[Dispatch] Failed: {e}")
        return {"error": str(e)}


# ─────────────────────────────────────────────
# Task 5: Monthly Credit Reset
# ─────────────────────────────────────────────

@celery_app.task
def reset_monthly_credits():
    """Reset credits for paid users on the 1st of each month."""
    db = SessionLocal()
    try:
        from backend.payments import get_tier_credits  # type: ignore
        users = db.query(Users).filter(Users.tier.in_(["pro", "creator"])).all()
        count = 0
        for user in users:
            user.credits = get_tier_credits(user.tier)
            count += 1
        db.commit()
        logger.info(f"[Credits] Reset {count} users")
        return {"reset": count}
    except Exception as e:
        db.rollback()
        logger.error(f"[Credits] Reset failed: {e}")
        return {"error": str(e)}
    finally:
        db.close()


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
