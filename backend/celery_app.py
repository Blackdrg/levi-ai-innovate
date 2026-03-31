from celery import Celery # type: ignore
from celery.signals import setup_logging, task_prerun, task_postrun # type: ignore
import logging
import os
import sys
from pythonjsonlogger.json import JsonFormatter # type: ignore

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
IS_DEV = os.getenv("ENVIRONMENT", "development") == "development"
IS_WINDOWS = sys.platform == "win32"

# In dev: use in-memory broker so the worker starts without Redis installed.
# In production: use Redis as the real broker.
_BROKER = "memory://" if IS_DEV else REDIS_URL
_BACKEND = "cache+memory://" if IS_DEV else REDIS_URL

celery_app = Celery(
    "levi_tasks",
    broker=_BROKER,
    backend=_BACKEND,
    include=[
        "backend.services.studio.tasks",
        "backend.tasks",
        "backend.services.orchestrator.memory_tasks",  # Memory buffer flush tasks
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
    # Phase 6 Hardening: Reliability & Backpressure
    task_acks_late=True,                  # Only ACK once task is actually finished
    worker_prefetch_multiplier=1,          # Don't hog tasks; pull one at a time
    task_reject_on_worker_lost=True,       # Reschedule if worker crashes during task
    worker_send_task_events=True,          # Essential for real-time flower monitoring
    task_queue_max_priority=10,            # Support priority routing if added

    # ── Local Dev: run tasks inline, no broker/worker needed ──────────
    # Set ENVIRONMENT=production to disable this.
    task_always_eager=IS_DEV,
    task_eager_propagates=IS_DEV,
    # ── Windows: prefork pool has WinError 5 semaphore issues ─────────
    # Use 'solo' pool on Windows to avoid PermissionError on billiard.
    worker_pool="solo" if IS_WINDOWS else "prefork",
)

# ── Celery Beat: Periodic Task Schedule ──────────────────────
# IMPORTANT: Requires `celery -A backend.celery_app beat` running as a separate process.
celery_app.conf.beat_schedule = {
    "flush-memory-buffers-every-30s": {
        "task": "backend.services.orchestrator.memory_tasks.flush_all_memory_buffers",
        "schedule": 30.0,
    },
    "flush-conv-buffer-every-minute": {
        "task": "backend.services.orchestrator.memory_tasks.flush_conversation_buffer",
        "schedule": 60.0,
    },
    "global-memory-maintenance-12h": {
        "task": "backend.services.orchestrator.memory_tasks.run_global_maintenance",
        "schedule": 43200.0, # 12 hours
    },
    "daily-faiss-garbage-collection": {
        "task": "backend.services.orchestrator.memory_tasks.garbage_collect_memory",
        "schedule": 86400.0, # 24 hours
    }
}

# ── Thread-local task context for log enrichment ─────────────
import threading
_task_context = threading.local()

@task_prerun.connect
def set_task_context(task_id=None, task=None, **kwargs):
    """Inject task_id into thread-local so WorkerJsonFormatter can access it."""
    _task_context.task_id = task_id or "none"
    _task_context.task_name = task.name if task else "unknown"

@task_postrun.connect
def clear_task_context(**kwargs):
    """Clear task context after task completes."""
    _task_context.task_id = "none"
    _task_context.task_name = "unknown"


class WorkerJsonFormatter(JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(WorkerJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            from datetime import datetime
            log_record['timestamp'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname
        log_record['instance_id'] = os.getenv("INSTANCE_ID", "worker")
        # Enrich with Celery task context for Cloud Logging correlation
        log_record['task_id'] = getattr(_task_context, 'task_id', 'none')
        log_record['task_name'] = getattr(_task_context, 'task_name', 'unknown')
        log_record['worker_name'] = os.getenv("CELERY_WORKER_NAME", "worker-default")


@setup_logging.connect
def config_loggers(*args, **kwtags):
    logger = logging.getLogger()
    logHandler = logging.StreamHandler()
    formatter = WorkerJsonFormatter(fmt='%(timestamp)s %(level)s %(name)s %(message)s') # type: ignore
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)

if __name__ == "__main__":
    celery_app.start()
