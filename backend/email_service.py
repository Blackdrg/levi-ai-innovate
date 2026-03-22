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

def send_payment_receipt(user_email: str, plan: str, amount_inr: float):
    """
    Sends a payment confirmation receipt via email using Resend.
    """
    if not RESEND_API_KEY:
        logger.warning("Resend API key missing. Payment receipt not sent.")
        return False

    try:
        params = {
            "from": "LEVI <noreply@resend.dev>",
            "to": [user_email],
            "subject": f"Payment confirmed — LEVI {plan.title()} plan ✨",
            "html": f"""
                <div style="font-family: sans-serif; padding: 20px; color: #333; max-width: 600px; margin: auto; border: 1px solid #eee; border-radius: 12px;">
                    <h2 style="color: #6366f1; text-align: center;">Payment Confirmed</h2>
                    <p>Greetings seeker,</p>
                    <p>Your payment of <b>₹{amount_inr}</b> has been received and confirmed.</p>
                    <p>Your account has been successfully upgraded to the <b>{plan.title()}</b> plan. You now have full access to premium artistic synthesis and expanded wisdom generation.</p>
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="https://levi-ai.create.app/studio.html" style="background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;">Enter the Studio</a>
                    </div>
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
                    <small style="color: #999;">Transaction processed via Razorpay Secure. If you have any questions, simply reply to this email.</small>
                </div>
            """
        }
        
        response = resend.Emails.send(params)
        logger.info(f"Payment receipt sent to {user_email}. ID: {response['id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to send payment receipt to {user_email}: {e}")
        return False
