# pyright: reportMissingImports=false
import os
import resend  # type: ignore
import logging
from backend.firestore_db import db as firestore_db  # type: ignore
try:
    from backend.generation import generate_quote  # type: ignore
except ImportError:
    from generation import generate_quote  # type: ignore

from typing import Optional, Any

logger = logging.getLogger(__name__)

# Resend API key
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY # type: ignore
    logger.info("Resend initialized.")

def send_daily_quote(user_email: str, user_name: str, liked_topics: Optional[list] = None, last_mood: str = "philosophical"):
    """
    Sends a personalized daily quote via email using Resend.
    """
    if not RESEND_API_KEY:
        logger.warning("Resend API key missing. Email not sent.")
        return False

    try:
        topic = liked_topics[0] if liked_topics else "wisdom"
        quote_text = generate_quote(prompt=topic, mood=last_mood)
        
        params: Any = {
            "from": os.getenv("RESEND_SENDER", "onboarding@resend.dev"), # Default sender for Resend free tier
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
                    <small>Sent with 💜 by LEVI-AI</small>
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

    try:

        params: Any = {

            "from": os.getenv("RESEND_SENDER", "onboarding@resend.dev"),

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

def send_verification_email(user_email: str, token: str):
    """
    Sends a verification email with a signed token link.
    """
    if not RESEND_API_KEY:
        logger.warning("Resend API key missing. Verification email not sent.")
        return False

    frontend_url = os.getenv("FRONTEND_URL", "https://levi-ai.create.app")
    verify_link = f"{frontend_url}/verify?token={token}"

    try:
        params: Any = {
            "from": os.getenv("RESEND_SENDER", "onboarding@resend.dev"),
            "to": [user_email],
            "subject": "Verify your LEVI account ✨",
            "html": f"""
                <div style="font-family: sans-serif; padding: 20px; color: #333; max-width: 600px; margin: auto; border: 1px solid #eee; border-radius: 12px;">
                    <h2 style="color: #6366f1; text-align: center;">Welcome to LEVI</h2>
                    <p>Greetings seeker,</p>
                    <p>Thank you for joining LEVI. Please verify your email address to activate your account and start generating wisdom.</p>
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{verify_link}" style="background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;">Verify Email</a>
                    </div>
                    <p style="margin-top: 20px; font-size: 0.9em; color: #666;">If the button doesn't work, copy and paste this link: <br>{verify_link}</p>
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
                    <small style="color: #999;">Sent with 💜 by LEVI-AI</small>
                </div>
            """
        }
        
        response = resend.Emails.send(params)
        logger.info(f"Verification email sent to {user_email}. ID: {response['id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {user_email}: {e}")
        return False

def send_password_reset_email(user_email: str, token: str):
    """
    Sends a password reset email with a signed token link.
    """
    if not RESEND_API_KEY:
        logger.warning("Resend API key missing. Reset email not sent.")
        return False

    frontend_url = os.getenv("FRONTEND_URL", "https://levi-ai.create.app")
    reset_link = f"{frontend_url}/reset-password.html?token={token}"

    try:
        params: Any = {
            "from": os.getenv("RESEND_SENDER", "onboarding@resend.dev"),
            "to": [user_email],
            "subject": "Reset your LEVI password ✨",
            "html": f"""
                <div style="font-family: sans-serif; padding: 20px; color: #333; max-width: 600px; margin: auto; border: 1px solid #eee; border-radius: 12px;">
                    <h2 style="color: #6366f1; text-align: center;">Reset Your Password</h2>
                    <p>Greetings seeker,</p>
                    <p>We received a request to reset your LEVI account password. If this wasn't you, you can safely ignore this email.</p>
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{reset_link}" style="background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;">Reset Password</a>
                    </div>
                    <p style="margin-top: 20px; font-size: 0.9em; color: #666;">This link will expire in 1 hour. If the button doesn't work, copy and paste this link: <br>{reset_link}</p>
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
                    <small style="color: #999;">Sent with 💜 by LEVI-AI</small>
                </div>
            """
        }
        
        response = resend.Emails.send(params)
        logger.info(f"Password reset email sent to {user_email}. ID: {response['id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user_email}: {e}")
        return False
