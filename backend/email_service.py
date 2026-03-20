import os
import resend
import logging
try:
    from backend.generation import generate_quote
except ImportError:
    from generation import generate_quote

logger = logging.getLogger(__name__)

# Resend API key
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
    logger.info("Resend initialized.")

def send_daily_quote(user_email: str, user_name: str, liked_topics: list = None, last_mood: str = "philosophical"):
    """
    Sends a personalized daily quote via email using Resend.
    """
    if not RESEND_API_KEY:
        logger.warning("Resend API key missing. Email not sent.")
        return False

    try:
        topic = liked_topics[0] if liked_topics else "wisdom"
        quote_text = generate_quote(prompt=topic, mood=last_mood)
        
        params = {
            "from": "LEVI <onboarding@resend.dev>", # Default sender for Resend free tier
            "to": [user_email],
            "subject": f"Your daily wisdom, {user_name} ✨",
            "html": f"""
                <div style="font-family: sans-serif; padding: 20px; color: #333;">
                    <h2 style="color: #6366f1;">Your Daily Muse</h2>
                    <blockquote style="font-style: italic; font-size: 1.2em; border-left: 4px solid #6366f1; padding-left: 15px;">
                        "{quote_text}"
                    </blockquote>
                    <p style="margin-top: 20px;">Stay inspired today!</p>
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    <small>Sent with 💜 by LEVI AI</small>
                </div>
            """
        }
        
        response = resend.Emails.send(params)
        logger.info(f"Daily quote sent to {user_email}. ID: {response['id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {user_email}: {e}")
        return False
