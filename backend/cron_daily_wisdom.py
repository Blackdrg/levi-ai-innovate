# pyright: reportMissingImports=false
import os
import logging
from sqlalchemy.orm import Session  # type: ignore
from backend.db import SessionLocal  # type: ignore
from backend.models import Users, UserMemory  # type: ignore
from backend.email_service import send_daily_quote  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from typing import List, Optional

def run_daily_wisdom():
    """
    Iterates through all users and sends them their personalized daily wisdom email.
    To be run daily via a cron job (e.g., on Render).
    """
    db = SessionLocal()
    try:
        users: List[Users] = db.query(Users).filter(Users.is_verified == 1).all()
        logger.info(f"Starting daily wisdom run for {len(users)} verified users...")
        
        for user in users:
            # Simple heuristic: user.username must be an email for this to work
            if not user.username or "@" not in user.username:
                logger.warning(f"Skipping user {user.username}: Username not an email.")
                continue
                
            user_mem: Optional[UserMemory] = db.query(UserMemory).filter(UserMemory.user_id == user.id).first()
            topics = user_mem.liked_topics if user_mem else ["wisdom"]
            mood = user_mem.mood_history[-1] if user_mem and user_mem.mood_history else "philosophical"
            
            logger.info(f"Sending daily wisdom to {user.username} (Mood: {mood}, Topic: {topics[0] if topics else 'N/A'})")
            success = send_daily_quote(
                user_email=str(user.username),
                user_name=str(user.username).split('@')[0],
                liked_topics=list(topics),
                last_mood=str(mood)
            )
            
            if not success:
                logger.error(f"Failed to send email to {user.username}.")
                
        logger.info("Daily wisdom run complete.")
    except Exception as e:
        logger.error(f"Daily wisdom run failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_daily_wisdom()
