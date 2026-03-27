import os
from celery import Celery # type: ignore

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "levi_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "backend.services.studio.tasks",
        "backend.tasks"
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    worker_concurrency=int(os.getenv("CELERY_CONCURRENCY", "4")),
)

if __name__ == "__main__":
    celery_app.start()
