# backend/services/notifications/email.py
import os
import logging
from typing import Optional, Any
import resend  # type: ignore

logger = logging.getLogger(__name__)

# Resend API key
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
    logger.info("Resend initialized for notification service.")

def send_email_notification(to_email: str, subject: str, html_content: str):
    """Generic email sender using Resend."""
    if not RESEND_API_KEY:
        logger.warning("Resend API key missing.")
        return False
    try:
        params: Any = {
            "from": os.getenv("RESEND_SENDER", "onboarding@resend.dev"),
            "to": [to_email],
            "subject": subject,
            "html": html_content
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        logger.error(f"Email failure to {to_email}: {e}")
        return False

def send_welcome_email(user_email: str, user_name: str):
    subject = f"Welcome to the Sovereign Mind, {user_name} ✨"
    html = f"<div><h2>Greetings seeker.</h2><p>Your journey with LEVI begins now.</p></div>"
    return send_email_notification(user_email, subject, html)

def send_payment_success_email(user_email: str, plan: str, amount: float):
    subject = f"Payment Confirmed — Plan: {plan.title()} ✨"
    html = f"<div><h2>Payment Received</h2><p>Your account is now upgraded to {plan}.</p></div>"
    return send_email_notification(user_email, subject, html)
