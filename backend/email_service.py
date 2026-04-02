"""
Sovereign Communication Layer (Email) v7.
Hardened for global notifications and daily wisdom dispatch.
Integrated with SovereignI18n for multilingual outreach.
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText # type: ignore
from email.mime.multipart import MIMEMultipart # type: ignore
from typing import Dict, Any, List, Optional
from backend.engines.utils.i18n import SovereignI18n

logger = logging.getLogger(__name__)

# --- Configuration ---
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.sendgrid.net")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "apikey")
SMTP_PASS = os.getenv("SMTP_PASS", None)
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "oracle@levi-ai.create.app")

class SovereignMail:
    """
    Sovereign Mail Dispatcher.
    Coordinates between engine-level events and user notifications.
    Supports markdown-to-html transformation and I18n templates.
    """
    
    @staticmethod
    def send_notification(
        to_email: str, 
        subject_key: str, 
        body_key: str, 
        lang: str = "en", 
        context: Dict[str, Any] = {}
    ) -> bool:
        """Sends a multilingual Sovereign notification."""
        if not SMTP_PASS:
            logger.warning("[Mail] API Credentials missing. Suppressing outreach.")
            return False
            
        # Retrieval of I18n templates
        subject = SovereignI18n.get_prompt(subject_key, lang).format(**context)
        body = SovereignI18n.get_prompt(body_key, lang).format(**context)
        
        logger.info(f"[Mail] Dispatching global wisdom to {to_email} ({lang})")
        
        try:
            msg = MIMEMultipart()
            msg["From"] = SENDER_EMAIL
            msg["To"] = to_email
            msg["Subject"] = f"LEVI Sovereign: {subject}"
            
            # Simple text/html synthesis
            msg.attach(MIMEText(body, "plain"))
            
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
                
            logger.info(f"[Mail] Outreach successful: {to_email}")
            return True
        except Exception as e:
            logger.error(f"[Mail] Critical outreach failure for {to_email}: {e}")
            return False

# Global Accessor
def dispatch_mail(**kwargs) -> bool:
    return SovereignMail.send_notification(**kwargs)
