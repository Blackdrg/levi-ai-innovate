import os
import uuid
import logging
import boto3
from io import BytesIO
from celery import Celery
from botocore.exceptions import BotoCoreError, ClientError
from pywebpush import webpush, WebPushException

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Celery setup — uses Redis as broker
# ─────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
celery_app = Celery("levi", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    result_expires=3600,  # Results expire after 1 hour
)


# ─────────────────────────────────────────────
# S3 helper
# ─────────────────────────────────────────────
def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name           = os.getenv("AWS_REGION", "us-east-1"),
    )


def upload_to_s3(file_bytes: bytes, filename: str, content_type: str = "video/mp4") -> str:
    """
    Upload bytes to S3. Returns the public URL.
    Bucket must have public-read ACL or use CloudFront.
    """
    bucket = os.getenv("AWS_S3_BUCKET", "levi-media")
    s3     = get_s3_client()

    try:
        s3.put_object(
            Bucket      = bucket,
            Key         = filename,
            Body        = file_bytes,
            ContentType = content_type,
        )
        region = os.getenv("AWS_REGION", "us-east-1")
        url = f"https://{bucket}.s3.{region}.amazonaws.com/{filename}"
        logger.info(f"Uploaded to S3: {url}")
        return url

    except (BotoCoreError, ClientError) as e:
        logger.error(f"S3 upload failed: {e}")
        raise


def upload_image_to_s3(image_bytes: bytes, user_id: int) -> str:
    filename = f"images/{user_id}/{uuid.uuid4().hex}.png"
    return upload_to_s3(image_bytes, filename, content_type="image/png")


def upload_video_to_s3(video_bytes: bytes, user_id: int) -> str:
    filename = f"videos/{user_id}/{uuid.uuid4().hex}.mp4"
    return upload_to_s3(video_bytes, filename, content_type="video/mp4")


# ─────────────────────────────────────────────
# Task 1: Generate quote image in background
# ─────────────────────────────────────────────
@celery_app.task(bind=True, max_retries=2)
def generate_image_task(self, quote: str, author: str, mood: str, user_id: int):
    """
    Generate image via Together.AI + upload to S3.
    Returns the S3 URL.
    """
    try:
        from backend.image_gen import generate_quote_image
        from backend.models import FeedItem, Users
        from backend.db import SessionLocal
        logger.info(f"[Task] Generating image for user {user_id}")

        db = SessionLocal()
        user_tier = "free"
        try:
            user = db.query(Users).filter(Users.id == user_id).first()
            if user:
                user_tier = user.tier
        finally:
            db.close()

        bio = generate_quote_image(quote, author, mood, user_tier=user_tier)
        img_bytes = bio.getvalue()

        # Store in S3 if configured, otherwise return base64
        image_url = None
        image_b64 = None
        
        if os.getenv("AWS_S3_BUCKET"):
            image_url = upload_image_to_s3(img_bytes, user_id)
        else:
            import base64
            image_b64 = "data:image/png;base64," + base64.b64encode(img_bytes).decode()

        # Save to FeedItem for persistence
        db = SessionLocal()
        try:
            new_item = FeedItem(
                user_id=user_id,
                text=quote,
                author=author,
                mood=mood,
                image_url=image_url,
                image_b64=image_b64
            )
            db.add(new_item)
            db.commit()
            db.refresh(new_item)
            return {
                "status": "done", 
                "url": image_url or image_b64, 
                "id": new_item.id,
                "type": "s3" if image_url else "base64"
            }
        finally:
            db.close()

    except Exception as e:
        logger.error(f"[Task] Image generation failed: {e}")
        raise self.retry(exc=e, countdown=5)


# ─────────────────────────────────────────────
# Task 2: Generate quote VIDEO in background
# ─────────────────────────────────────────────
@celery_app.task(bind=True, max_retries=1)
def generate_video_task(self, quote: str, author: str, mood: str, user_id: int):
    """
    Generate a Reels-ready MP4 video and upload to S3.
    """
    try:
        from backend.models import FeedItem
        from backend.db import SessionLocal
        logger.info(f"[Task] Generating video for user {user_id}")
        video_bytes = _create_quote_video(quote, author, mood)

        video_url = None
        if os.getenv("AWS_S3_BUCKET"):
            video_url = upload_video_to_s3(video_bytes, user_id)
        
        # Save to FeedItem for persistence
        db = SessionLocal()
        try:
            new_item = FeedItem(
                user_id=user_id,
                text=quote,
                author=author,
                mood=mood,
                video_url=video_url
            )
            db.add(new_item)
            db.commit()
            db.refresh(new_item)
            return {
                "status": "done", 
                "url": video_url, 
                "id": new_item.id,
                "type": "s3" if video_url else "local"
            }
        finally:
            db.close()

    except Exception as e:
        logger.error(f"[Task] Video generation failed: {e}")
        raise self.retry(exc=e, countdown=10)


# ─────────────────────────────────────────────
# Task 3: Send Push Notification
# ─────────────────────────────────────────────
@celery_app.task(bind=True, max_retries=3)
def send_push_notification_task(self, endpoint, p256dh, auth, title, body):
    """
    Sends a Web Push notification to a specific subscription.
    """
    try:
        private_key = os.getenv("VAPID_PRIVATE_KEY")
        claims = {"sub": "mailto:" + os.getenv("VAPID_ADMIN_EMAIL", "admin@levi-ai.create.app")}
        
        if not private_key:
            logger.error("VAPID_PRIVATE_KEY not set. Cannot send push notification.")
            return False

        webpush(
            subscription_info={
                "endpoint": endpoint,
                "keys": {"p256dh": p256dh, "auth": auth}
            },
            data=body, # You can also send JSON here if sw.js handles it
            vapid_private_key=private_key,
            vapid_claims=claims
        )
        logger.info(f"Push notification sent to {endpoint}")
        return True

    except WebPushException as ex:
        logger.error(f"WebPush error: {ex}")
        # If subscription is no longer valid (410 Gone), we should ideally remove it from DB
        # But we don't have user_id here. A more robust implementation would pass subscription ID.
        if ex.response and ex.response.status_code == 410:
            logger.warning("Subscription expired/gone. Should be removed.")
        raise self.retry(exc=ex, countdown=60)
    except Exception as e:
        logger.error(f"Push notification failed: {e}")
        raise self.retry(exc=e, countdown=60)


def _create_quote_video(quote: str, author: str, mood: str) -> bytes:
    """Creates an 9:16 vertical video (Instagram Reel format)."""
    try:
        try:
            from moviepy import ImageClip, TextClip, CompositeVideoClip, AudioFileClip
        except ImportError:
            from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, AudioFileClip
        
        from backend.image_gen import generate_quote_image

        # Generate background image
        bio = generate_quote_image(quote, author, mood, size=(1080, 1920))
        img_path = f"/tmp/bg_{uuid.uuid4().hex}.png"
        with open(img_path, "wb") as f:
            f.write(bio.getvalue())

        duration = 8  # seconds
        clip = ImageClip(img_path).set_duration(duration)

        # Compose final video
        final = CompositeVideoClip([clip])
        output_path = f"/tmp/video_{uuid.uuid4().hex}.mp4"
        final.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio=False,
            logger=None  # Suppress moviepy logs
        )

        with open(output_path, "rb") as f:
            video_bytes = f.read()

        # Cleanup temp files
        os.remove(img_path)
        os.remove(output_path)

        return video_bytes

    except ImportError:
        raise RuntimeError("moviepy not installed. Run: pip install moviepy")


# ─────────────────────────────────────────────
# Task 3: Send daily quote email
# ─────────────────────────────────────────────
@celery_app.task
def send_daily_quote_email(user_email: str, user_id: int, liked_topics: list):
    """Send personalized daily quote via Resend (free tier: 3000/month)."""
    resend_key = os.getenv("RESEND_API_KEY")
    if not resend_key:
        logger.warning("RESEND_API_KEY not set — skipping email")
        return

    try:
        from backend.generation import generate_quote
        topic = liked_topics[0] if liked_topics else "life"
        quote = generate_quote(topic)

        import requests
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {resend_key}",
                "Content-Type": "application/json",
            },
            json={
                "from":    "LEVI AI <daily@yourdomain.com>",
                "to":      [user_email],
                "subject": "Your daily wisdom ✨",
                "html":    f"""
                    <div style="font-family:Georgia;max-width:600px;margin:auto;padding:40px;background:#050B14;color:white;border-radius:16px">
                        <h2 style="color:#8B5CF6;text-align:center">LEVI AI</h2>
                        <p style="font-size:24px;font-style:italic;text-align:center;line-height:1.6">"{quote}"</p>
                        <div style="text-align:center;margin-top:30px">
                            <a href="{os.getenv('FRONTEND_URL', 'http://localhost:8080')}/chat.html"
                               style="background:#8B5CF6;color:white;padding:12px 24px;border-radius:8px;text-decoration:none">
                               Get More Wisdom →
                            </a>
                        </div>
                    </div>
                """
            }
        )
        logger.info(f"Daily email sent to {user_email}: {resp.status_code}")

    except Exception as e:
        logger.error(f"Email send failed for {user_email}: {e}")


# ─────────────────────────────────────────────
# Celery Beat schedule (cron jobs)
# ─────────────────────────────────────────────
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # Send daily quotes every morning at 8 AM
    "daily-quote-emails": {
        "task":     "backend.tasks.dispatch_daily_emails",
        "schedule": crontab(hour=8, minute=0),
    },
}


@celery_app.task
def dispatch_daily_emails():
    """Fetch all users and dispatch daily quote tasks (Email + Push)."""
    try:
        from backend.db import SessionLocal
        from backend.models import Users, PushSubscription
        from backend.generation import generate_quote
        db = SessionLocal()
        
        users = db.query(Users).all()
        for user in users:
            topics = getattr(user, "liked_topics", []) or ["life"]
            
            # 1. Dispatch Email if available
            if user.email:
                send_daily_quote_email.delay(user.email, user.id, topics)
            
            # 2. Dispatch Push Notifications if subscribed
            subs = db.query(PushSubscription).filter(PushSubscription.user_id == user.id).all()
            if subs:
                quote = generate_quote(topics[0] if topics else "life")
                for s in subs:
                    send_push_notification_task.delay(
                        s.endpoint, s.p256dh, s.auth, 
                        "Your Daily Wisdom ✨", quote
                    )
                    
        db.close()
        logger.info(f"Dispatched daily wisdom to {len(users)} users")
    except Exception as e:
        logger.error(f"dispatch_daily_emails failed: {e}")