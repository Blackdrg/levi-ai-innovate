"""
Sovereign Webhook Dispatcher v14.1.0.
Reliable event delivery with Celery-backed retries and exponential backoff.
"""

import logging
import httpx
from backend.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(
    bind=True,
    name="backend.core.webhook_tasks.dispatch_webhook",
    max_retries=5,
    default_retry_delay=60, # 1 minute base
)
def dispatch_webhook(self, url: str, payload: dict, secret: str = None):
    """
    Dispatches a webhook payload with exponential backoff.
    """
    try:
        # 1. Sign payload if secret provided (Sovereign HMAC-SHA256)
        headers = {"Content-Type": "application/json"}
        if secret:
            import hmac
            import hashlib
            import json
            signature = hmac.new(
                secret.encode(), 
                json.dumps(payload, sort_keys=True).encode(), 
                hashlib.sha256
            ).hexdigest()
            headers["X-Sovereign-Signature"] = signature

        # 2. Synchronous request (running inside Celery worker)
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
        logger.info(f"[Webhook] Successfully dispatched to {url}")
        return {"status": "success", "url": url}

    except Exception as exc:
        logger.warning(f"[Webhook] Dispatch failed to {url}: {exc}. Retrying...")
        # 3. Exponential Backoff: 1m, 2m, 4m, 8m, 16m...
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

class WebhookDispatcher:
    """
    Entry point for the Orchestrator to emit events to external systems.
    """
    @staticmethod
    def emit(event_type: str, payload: dict, url: str, secret: str = None):
        """Asynchronously dispatches a webhook via Celery."""
        full_payload = {
            "event": event_type,
            "data": payload,
            "timestamp": "v14.1-Autonomous"
        }
        dispatch_webhook.delay(url, full_payload, secret=secret)
        logger.info(f"[Webhook] Queued {event_type} for {url}")
