"""
LEVI-AI Security Alerting Engine v14.1.
Routes high-threat security events to admin notifications.
"""

import logging
import os
from datetime import datetime, timezone

from backend.services.notifications.tasks import send_push_notification_task
from backend.db.firestore_db import db as firestore_db

logger = logging.getLogger(__name__)

class AlertingEngine:
    ADMIN_USER_ID = os.getenv("ADMIN_USER_ID", "admin_root")

    @classmethod
    async def trigger_security_alert(cls, threat_score: float, details: dict):
        """Dispatches a high-priority security alert."""
        timestamp = datetime.now(timezone.utc).isoformat()
        alert_msg = f"SECURITY ALERT ({int(threat_score*100)}%): {details.get('reason', 'Anomaly detected')}"
        
        logger.error(f"[Alert] {alert_msg}")

        # 1. Log to Persistence
        try:
            await firestore_db.collection("security_alerts").add({
                "severity": "CRITICAL" if threat_score >= 0.9 else "WARNING",
                "score": threat_score,
                "details": details,
                "timestamp": timestamp
            })
        except Exception:
            pass

        # 2. Push notification to Admin
        try:
            subs = firestore_db.collection("push_subscriptions").where("user_id", "==", cls.ADMIN_USER_ID).stream()
            for sub in subs:
                s = sub.to_dict()
                send_push_notification_task.delay(
                    sub.id,
                    s.get("endpoint"),
                    s.get("p256dh"),
                    s.get("auth"),
                    "LEVI SECURITY PULSE",
                    alert_msg
                )
        except Exception as e:
            logger.warning(f"[Alert] Push notification failed: {e}")
