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
        "backend.services.notifications.tasks",
        "backend.services.payments.tasks",
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
# IMPORTANT: Requires `celery -A backend.celery_app beat` running as a separate process.
celery_app.conf.beat_schedule = {
    "flush-memory-buffers-every-30s": {
        "task": "backend.core.memory_tasks.flush_all_memory_buffers",
        "schedule": 30.0,
    },
    "sovereign-dreaming-cycle-4h": {
        "task": "backend.core.memory_tasks.dream_all_users",
        "schedule": 14400.0, # Every 4 hours (distillation)
    },
    "self-healing-monitor-5m": {
        "task": "backend.core.critic_tasks.process_failure_queue",
        "schedule": 300.0, # Every 5 mins
    },
    "global-evolution-daily": {
        "task": "backend.core.learning_tasks.run_autonomous_evolution",
        "schedule": 86400.0, # Daily (3 AM default)
    },
    "studio-stuck-job-cleanup-every-hour": {
        "task": "backend.services.studio.tasks.cleanup_stuck_jobs",
        "schedule": 3600.0,
    },
    "daily-wisdom-dispatch": {
        "task": "backend.services.notifications.tasks.dispatch_daily_emails",
        "schedule": crontab(hour=8, minute=0),
    },
    "monthly-credit-reset": {
        "task": "backend.services.payments.tasks.reset_monthly_credits",
        "schedule": crontab(day_of_month=1, hour=0, minute=5),
    },
    # ── Phase 6: Unbound Training Array ──────────────────────
    "unbound-training-cycle-weekly": {
        "task": "backend.core.learning_tasks.unbound_training_cycle",
        "schedule": crontab(hour=0, minute=0, day_of_week=0), # Weekly on Sunday
    },
    "survival-hygiene-weekly": {
        "task": "backend.core.memory_tasks.run_survival_hygiene",
        "schedule": crontab(hour=0, minute=0, day_of_week=0), # Weekly on Sunday
    },
    "poll-training-status-4h": {
        "task": "backend.core.learning_tasks.poll_training_status",
        "schedule": 14400.0, # Every 4 hours
    },
    "trigger-scheduled-missions-60s": {
        "task": "backend.services.scheduling.trigger_scheduled_missions",
        "schedule": 60.0,
    },
    "daily-compliance-sweep": {
        "task": "backend.jobs.audit_jobs.run_daily_compliance_sweep",
        "schedule": crontab(hour=2, minute=0), # 2 AM Daily
    },
    "nightly-maintenance-suite": {
        "task": "backend.jobs.maintenance.run_full_maintenance_suite",
        "schedule": crontab(hour=3, minute=0), # 3 AM Daily
    },
    "sovereign-shadow-audit-6h": {
        "task": "backend.services.orchestrator.learning_tasks.run_shadow_audit_task",
        "schedule": 21600.0, # Every 6 hours
    },
    "pattern-crystallization-4h": {
        "task": "backend.services.orchestrator.learning_tasks.crystallize_patterns_task",
        "schedule": 14400.0, # Every 4 hours
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
    _task_context.start_time = time.time()

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
