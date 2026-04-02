"""
Sovereign Celery v8.
Central Celery application for background execution and periodic Cog-Ops.
"""

from celery import Celery # type: ignore
import logging
import os
import sys

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
IS_DEV = os.getenv("ENVIRONMENT", "development") == "development"
IS_WINDOWS = sys.platform == "win32"

_BROKER = "memory://" if IS_DEV else REDIS_URL
_BACKEND = "cache+memory://" if IS_DEV else REDIS_URL

celery_app = Celery(
    "levi_workers",
    broker=_BROKER,
    backend=_BACKEND,
    # Points to redesigned task locations
    include=[
        "backend.workers.tasks.studio",
        "backend.workers.tasks.memory",
        "backend.workers.tasks.learning",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_concurrency=int(os.getenv("CELERY_CONCURRENCY", "4")),
    worker_pool="solo" if IS_WINDOWS else "prefork",
)

# Unified Evolution & Maintenance Schedule
celery_app.conf.beat_schedule = {
    "memory-distillation-daily": {
        "task": "backend.workers.tasks.memory.run_distillation",
        "schedule": 86400.0,
    },
    "studio-cleanup-hourly": {
        "task": "backend.workers.tasks.studio.cleanup_stuck_jobs",
        "schedule": 3600.0,
    }
}

if __name__ == "__main__":
    celery_app.start()
