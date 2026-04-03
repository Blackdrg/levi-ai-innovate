import os
import firebase_admin
from firebase_admin import credentials, messaging
from typing import Dict, Any, Optional
from backend.core.logger import logger

class NotificationService:
    """
    Autonomous Notification Service for the LEVI-AI Sovereign OS.
    Handles critical mission alerts, evolution pulses, and system failures.
    """
    def __init__(self):
        self._initialized = False
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Initializes Firebase Admin SDK."""
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-adminsdk.json")
        if os.path.exists(cred_path):
            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                self._initialized = True
                logger.info("Sovereign Link: Firebase Notification Service Initialized.")
            except Exception as e:
                logger.error(f"Fidelity Breach: Firebase Initialization Failed - {str(e)}")
        else:
            logger.warning("Sovereign Link: firebase-adminsdk.json missing. Push notifications disabled.")

    def send_mission_alert(self, user_id: str, title: str, body: str, data: Optional[Dict[str, Any]] = None):
        """Sends a mission-critical push notification to the Sovereign Link."""
        if not self._initialized:
            logger.debug(f"Push Handover: Notification suppressed (Firebase dummy mode) - {title}")
            return

        message = messaging.Message(
            notification=messaging.Notification(
                title=f"LEVI: {title}",
                body=body
            ),
            data=data or {},
            topic=f"user_{user_id}"
        )

        try:
            response = messaging.send(message)
            logger.info(f"Evolution Pulse: Push alert sent - {response}")
        except Exception as e:
            logger.error(f"Fidelity Breach: Push alert failure - {str(e)}")

    def alert_evolution_failure(self, user_id: str, error_msg: str):
        """Specialized alert for autonomous training array failures."""
        self.send_mission_alert(
            user_id=user_id,
            title="Evolution Breach",
            body=f"Autonomous training cycle failed: {error_msg}",
            data={"category": "evolution_failure", "priority": "high"}
        )

notification_service = NotificationService()
