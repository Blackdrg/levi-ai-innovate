import os
import json
import logging
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

class CloudTaskDispatcher:
    """
    Sovereign v14.1.0: GCP Cloud Tasks Dispatcher.
    Enqueues mission execution payloads for reliable distribution.
    """
    def __init__(self):
        self.client = tasks_v2.CloudTasksClient()
        self.project = os.getenv("GCP_PROJECT_ID")
        self.location = os.getenv("GCP_LOCATION", "us-central1")
        self.queue = os.getenv("GCP_CLOUD_TASKS_QUEUE", "mission-queue")
        self.webhook_url = os.getenv("CLOUD_TASKS_WEBHOOK_URL")

    def enqueue_mission(self, mission_id: str, payload: dict, delay_seconds: int = 0):
        """
        Dispatches a mission payload to the Cloud Task queue.
        """
        if not self.project or not self.webhook_url:
            logger.warning("[CloudTasks] Dispatcher not configured. Skipping enqueue.")
            return None

        parent = self.client.queue_path(self.project, self.location, self.queue)

        # Construct the Task
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": self.webhook_url,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "mission_id": mission_id,
                    "payload": payload,
                    "dispatched_at": datetime.now(timezone.utc).isoformat()
                }).encode(),
                # OIDC Token validation (GCP Native Security)
                "oidc_token": {
                    "service_account_email": os.getenv("GCP_SERVICE_ACCOUNT_EMAIL"),
                    "audience": self.webhook_url,
                },
            }
        }

        if delay_seconds > 0:
            d = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(d)
            task["schedule_time"] = timestamp

        try:
            response = self.client.create_task(request={"parent": parent, "task": task})
            logger.info(f"✅ [CloudTasks] Enqueued task {response.name} for mission {mission_id}")
            return response.name
        except Exception as e:
            logger.error(f"❌ [CloudTasks] Failed to enqueue mission {mission_id}: {e}")
            return None

# Singleton Instance
dispatcher = CloudTaskDispatcher()
