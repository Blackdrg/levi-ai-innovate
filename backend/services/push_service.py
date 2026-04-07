import logging
import os
import aiohttp
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PushService:
    """
    Sovereign Push Notification Hub.
    Bridges backend mission failure events to mobile companion apps.
    Supports Firebase (FCM) and OneSignal (default).
    """
    
    def __init__(self):
        self.os_app_id = os.getenv("ONESIGNAL_APP_ID")
        self.os_api_key = os.getenv("ONESIGNAL_API_KEY")
        self.fcm_server_key = os.getenv("FCM_SERVER_KEY")

    async def send_critical_alert(self, user_id: str, title: str, message: str, data: Dict[str, Any] = None):
        """
        Sends a high-priority push notification for a critical mission failure.
        """
        logger.info(f"[PushService] Sending critical alert to {user_id}: {title}")
        
        # 1. OneSignal implementation (Primary)
        if self.os_app_id and self.os_api_key:
            await self._send_onesignal(user_id, title, message, data)
        
        # 2. FCM implementation (Fallback/Parallel)
        if self.fcm_server_key:
            await self._send_fcm(user_id, title, message, data)
            
        if not self.os_app_id and not self.fcm_server_key:
            logger.warning("[PushService] Push infrastructure is unconfigured. Alert logged but not transmitted.")

    async def _send_onesignal(self, user_id: str, title: str, message: str, data: Dict[str, Any]):
        url = "https://onesignal.com/api/v1/notifications"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Basic {self.os_api_key}"
        }
        payload = {
            "app_id": self.os_app_id,
            "include_external_user_ids": [user_id],
            "headings": {"en": title},
            "contents": {"en": message},
            "data": data or {},
            "priority": 10 # High priority
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    result = await resp.json()
                    logger.debug(f"OneSignal response: {result}")
        except Exception as e:
            logger.error(f"OneSignal transmission failure: {e}")

    async def _send_fcm(self, user_id: str, title: str, message: str, data: Dict[str, Any]):
        # Implementation for FCM (Legacy/Cloud Messaging)
        url = "https://fcm.googleapis.com/fcm/send"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"key={self.fcm_server_key}"
        }
        # Note: This assumes user_id is mapped to a registration token in a DB
        # For LEVI-AI v8, we might use a topic based on user_id
        payload = {
            "to": f"/topics/user_{user_id}",
            "notification": {
                "title": title,
                "body": message,
                "sound": "default"
            },
            "data": data or {},
            "priority": "high"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                     logger.debug(f"FCM response status: {resp.status}")
        except Exception as e:
            logger.error(f"FCM transmission failure: {e}")
