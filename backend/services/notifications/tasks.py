import os
import logging
from typing import List, Optional
from datetime import datetime, timezone
from backend.celery_app import celery_app # type: ignore
from backend.db.firestore_db import db as firestore_db
from backend.services.notifications.email import send_email_notification
from backend.engines.chat.generation import generate_quote

try:
    from pywebpush import webpush, WebPushException # type: ignore
    HAS_WEBPUSH = True
except ImportError:
    HAS_WEBPUSH = False

logger = logging.getLogger(__name__)

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
        if hasattr(ex, 'response') and ex.response is not None:
            status = getattr(ex.response, 'status_code', None)
            if status in (410, 404):
                try:
                    firestore_db.collection("push_subscriptions").document(subscription_id).delete()
                    logger.info(f"[Push] Removed expired subscription {subscription_id}")
                except Exception:
                    pass
                return False
        logger.error(f"[Push] Failed: {ex}")
        raise self.retry(exc=ex)

@celery_app.task
def send_daily_quote_email(user_email: str, user_id: str, liked_topics: list, last_mood: str = "philosophical"):
    """Send personalized daily quote email."""
    try:
        topic = liked_topics[0] if liked_topics else "existence"
        quote = generate_quote(topic, mood=last_mood)
        
        subject = f"Your daily wisdom ✦ {topic.capitalize()}"
        html = f"<div style='font-family: serif; padding: 20px; border: 1px solid #ddd;'><h3>{topic.capitalize()}</h3><p style='font-size: 1.2em;'>{quote}</p></div>"
        
        send_email_notification(user_email, subject, html)
        logger.info(f"[Email] Sent daily quote to {user_email}")
    except Exception as e:
        logger.error(f"[Email] Error for {user_email}: {e}")

@celery_app.task
def dispatch_daily_emails():
    """Dispatch daily emails + push notifications to all users via Firestore."""
    try:
        users_ref = firestore_db.collection("users")
        dispatched = 0
        batch_size = 500
        last_doc = None

        while True:
            query = users_ref.limit(batch_size)
            if last_doc:
                query = query.start_after(last_doc)
            
            docs = list(query.get())
            if not docs:
                break
            
            for user_doc in docs:
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
            
            last_doc = docs[-1]

        logger.info(f"[Dispatch] Sent to {dispatched} users")
        return {"status": "completed", "dispatched": dispatched}
    except Exception as e:
        logger.error(f"[Dispatch] Failed: {e}")
        return {"error": str(e)}
