from celery import Celery # type: ignore
from celery.schedules import crontab # type: ignore
from celery.signals import setup_logging, task_prerun, task_postrun # type: ignore
import logging
import os
import sys
import time
from pythonjsonlogger.json import JsonFormatter # type: ignore
from prometheus_client import Counter, Histogram, REGISTRY # type: ignore

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
IS_DEV = os.getenv("ENVIRONMENT", "development") == "development"
IS_WINDOWS = sys.platform == "win32"

from backend.db.redis import get_celery_broker_url
_BROKER = "memory://" if IS_DEV else get_celery_broker_url()
_BACKEND = "cache+memory://" if IS_DEV else get_celery_broker_url()

celery_app = Celery(
    "levi_tasks",
    broker=_BROKER,
    backend=_BACKEND,
    include=[
        "backend.services.studio.tasks",
        "backend.services.notifications.tasks",
        "backend.services.payments.tasks",
        "backend.engines.brain.tasks",
        "backend.core.memory_tasks",

        "backend.core.learning_tasks",
        "backend.core.fine_tune_tasks",
        "backend.core.critic_tasks",
        "backend.jobs.audit_jobs",
        "backend.jobs.maintenance",
    ]
)

# ── Phase 16.1: API Worker Observability ──
TASK_COUNT = Counter(
    "leiva_worker_task_total", 
    "Total number of Celery tasks processed", 
    ["task_name", "status"]
)

TASK_LATENCY = Histogram(
    "leiva_worker_task_latency_seconds", 
    "Celery task latency in seconds", 
    ["task_name"]
)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # default 5 mins
    worker_concurrency=int(os.getenv("CELERY_CONCURRENCY", "4")),
    
    # ── Phase 11: Queue & Priority Routing ──
    task_queues={
        "high": {"exchange": "high", "routing_key": "high", "queue_arguments": {"x-max-priority": 10}},
        "default": {"exchange": "default", "routing_key": "default", "queue_arguments": {"x-max-priority": 5}},
        "heavy": {"exchange": "heavy", "routing_key": "heavy", "queue_arguments": {"x-max-priority": 1}},
        "dlq": {"exchange": "dlq", "routing_key": "dlq"},
    },
    task_routes={
        # Critical Brain Tasks -> High Priority
        "backend.core.critic_tasks.*": {"queue": "high", "priority": 10},
        "backend.core.memory_tasks.flush_all_memory_buffers": {"queue": "high", "priority": 9},
        
        # Heavy Tasks -> Heavy Queue
        "backend.services.studio.tasks.generate_video_task": {"queue": "heavy"},
        "backend.core.fine_tune_tasks.*": {"queue": "heavy"},
        
        # Everything Else -> Default
        "backend.services.studio.tasks.generate_image_task": {"queue": "default"},
        "backend.services.notifications.tasks.*": {"queue": "default"},
        "backend.services.payments.tasks.*": {"queue": "default"},
        "backend.core.*": {"queue": "default"},
        "*": {"queue": "default"},
    },
    
    # ── Dead-Letter Queue (DLQ) Strategy ──
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    
    # High-Priority / Heavy-Lift Overrides
    task_annotations={
        "backend.services.studio.tasks.generate_video_task": {
            "rate_limit": "2/m",        # Avoid overwhelming GPU/CPU
            "time_limit": 600,         # 10 mins for video
        },
        "*": {
             "on_failure": "backend.core.failure_engine.handle_celery_failure" # Custom DLQ bridge
        }
    },

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
# ALL legacy schedules have been migrated to Sovereign Event Streams.
# See backend/services/pulse_emitter.py for the autonomous rhythm.
celery_app.conf.beat_schedule = {}

# ── Thread-local task context for log enrichment ─────────────
import threading
_task_context = threading.local()

@task_prerun.connect
def set_task_context(task_id=None, task=None, **kwargs):
    """Inject task_id into thread-local and structlog context."""
    _task_context.task_id = task_id or "none"
    _task_context.task_name = task.name if task else "unknown"
    _task_context.start_time = time.time()
    
    # Sovereign v22.1: structlog and OTEL mission_id propagation
    import structlog
    from backend.utils.tracing import set_mission_baggage
    mission_id = "unknown"
    if 'args' in kwargs:
         for arg in kwargs['args']:
            if isinstance(arg, str) and (len(arg) == 36 or "mission" in str(arg).lower()): 
                mission_id = arg
                break
    if 'kwargs' in kwargs:
        mission_id = kwargs['kwargs'].get('mission_id', mission_id)
    
    structlog.contextvars.bind_contextvars(mission_id=mission_id, task_id=task_id)
    set_mission_baggage(mission_id)

@task_postrun.connect
def stop_task_timer(task_id=None, task=None, state=None, **kwargs):
    """Update Prometheus metrics after task completes."""
    if hasattr(_task_context, 'start_time'):
        latency = time.time() - _task_context.start_time
        TASK_LATENCY.labels(task_name=task.name if task else "unknown").observe(latency)
    
    TASK_COUNT.labels(
        task_name=task.name if task else "unknown",
        status=state or "UNKNOWN"
    ).inc()

@task_postrun.connect
def clear_task_context(**kwargs):

    """Clear task context after task completes."""
    _task_context.task_id = "none"
    _task_context.task_name = "unknown"
    import structlog
    structlog.contextvars.clear_contextvars()


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

# --- Integrated System Schedules ---
try:
    from backend.services.learning.trainer import TRAINING_BEAT_SCHEDULE # type: ignore
    celery_app.conf.beat_schedule.update(TRAINING_BEAT_SCHEDULE)
except ImportError:
    pass

if __name__ == "__main__":
    celery_app.start()
