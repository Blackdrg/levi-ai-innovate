from celery import Celery # type: ignore
from celery.signals import setup_logging, task_prerun, task_postrun # type: ignore
import logging
import os
import sys
from pythonjsonlogger.json import JsonFormatter # type: ignore

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
IS_DEV = os.getenv("ENVIRONMENT", "development") == "development"
IS_WINDOWS = sys.platform == "win32"

_BROKER = "memory://" if IS_DEV else REDIS_URL
_BACKEND = "cache+memory://" if IS_DEV else REDIS_URL

celery_app = Celery(
    "levi_tasks",
    broker=_BROKER,
    backend=_BACKEND,
    include=[
        "backend.services.studio.tasks",
        "backend.tasks",
        "backend.services.orchestrator.memory_tasks",
        "backend.services.learning.tasks", # Updated path
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_concurrency=int(os.getenv("CELERY_CONCURRENCY", "4")),
    
    task_routes={
        "backend.services.studio.tasks.generate_video_task": {"queue": "heavy"},
        "backend.services.studio.tasks.generate_image_task": {"queue": "default"},
        "*": {"queue": "default"},
    },
    
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    worker_send_task_events=True,
    worker_pool="solo" if IS_WINDOWS else "prefork",
)

celery_app.conf.beat_schedule = {
    "flush-memory-buffers-every-30s": {
        "task": "backend.services.orchestrator.memory_tasks.flush_all_memory_buffers",
        "schedule": 30.0,
    },
    "studio-stuck-job-cleanup-every-hour": {
        "task": "backend.services.studio.tasks.cleanup_stuck_jobs",
        "schedule": 3600.0,
    },
    "autonomous-prompt-evolution-daily": {
        "task": "backend.services.learning.tasks.run_autonomous_evolution",
        "schedule": 86400.0,
    },
    "analytics-snapshot-update-4h": {
        "task": "backend.services.learning.tasks.update_analytics_snapshot",
        "schedule": 14400.0,
    },
}

import threading
_task_context = threading.local()

@task_prerun.connect
def set_task_context(task_id=None, task=None, **kwargs):
    _task_context.task_id = task_id or "none"
    _task_context.task_name = task.name if task else "unknown"

@task_postrun.connect
def clear_task_context(**kwargs):
    _task_context.task_id = "none"
    _task_context.task_name = "unknown"

class WorkerJsonFormatter(JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(WorkerJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            from datetime import datetime
            log_record['timestamp'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        log_record['level'] = log_record.get('level', record.levelname).upper()
        log_record['instance_id'] = os.getenv("INSTANCE_ID", "worker")
        log_record['task_id'] = getattr(_task_context, 'task_id', 'none')

@setup_logging.connect
def config_loggers(*args, **kwtags):
    logger = logging.getLogger()
    logHandler = logging.StreamHandler()
    formatter = WorkerJsonFormatter(fmt='%(timestamp)s %(level)s %(name)s %(message)s')
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)

if __name__ == "__main__":
    celery_app.start()
