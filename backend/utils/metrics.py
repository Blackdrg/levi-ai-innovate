"""
Sovereign Metrics Hub v14.0.0.
Provides Prometheus-compatible telemetry for execution, observability, and backpressure.
"""

import logging
from typing import Optional

import psutil
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

logger = logging.getLogger(__name__)

# 1. System Health Metrics
VRAM_AVAILABLE = Gauge("vram_available_bytes", "Free VRAM available for neural inference")
CPU_USAGE = Gauge("cpu_usage_percent", "System CPU utilization")
RAM_USAGE = Gauge("ram_usage_bytes", "System RAM utilization")
EXECUTOR_QUEUE_DEPTH = Gauge("executor_queue_depth", "Current executor queue depth")
BACKPRESSURE_ACTIVE = Gauge(
    "executor_backpressure_active",
    "Backpressure signal for a resource dimension",
    ["resource"],
)

# 2. Mission & Agent Metrics
ACTIVE_MISSIONS = Gauge("active_missions", "Number of currently processing missions")
MISSION_COMPLETED = Counter("missions_completed_total", "Total successful missions")
MISSION_ABORTED = Counter("missions_aborted_total", "Total aborted/failed missions")
MISSION_FAILURES = Counter(
    "mission_failures_total",
    "Mission failures grouped by stage",
    ["stage"],
)
MISSION_CU = Histogram("mission_cu_consumption", "Cognitive Units consumed per mission")
COGNITIVE_UNITS_CONSUMED = Counter("cognitive_units_total", "Total cumulative Cognitive Units consumed")
AGENT_LATENCY = Histogram("agent_latency_ms", "Agent response latency in milliseconds", ["agent"])
NODE_LATENCY = Histogram(
    "node_latency_ms",
    "Node response latency in milliseconds",
    ["agent", "node_id"],
)
WAVE_SIZE = Histogram("executor_wave_size", "Number of nodes executed per wave")
DAG_DEPTH = Histogram("dag_depth_distribution", "Observed DAG depth distribution")
GPU_SEMAPHORE_AVAILABLE = Gauge("gpu_semaphore_available", "Number of available GPU task slots")
TOOL_CALLS_TOTAL = Counter("tool_calls_total", "Total executed tool calls", ["agent"])
TOKEN_CONSUMPTION = Counter("tokens_consumed_total", "Total consumed tokens", ["agent"])
TOOL_BUDGET_REJECTIONS = Counter(
    "tool_budget_rejections_total",
    "Budget rejections grouped by type",
    ["limit_type"],
)

# 3. Store Performance / Alerts / Tracing
FAISS_SEARCH_LATENCY = Histogram("faiss_search_ms", "FAISS semantic search latency")
REDIS_MEMORY = Gauge("redis_memory_bytes", "Redis memory consumption")
TRACE_STEP_LATENCY = Histogram(
    "trace_step_latency_ms",
    "Latency per traced pipeline step",
    ["step"],
)
ALERTS_TOTAL = Counter("alerts_total", "Total triggered alerts", ["alert_type", "severity"])
LAST_ALERT_STATE = Gauge(
    "last_alert_state",
    "Whether the most recent alert type is active",
    ["alert_type"],
)


class MetricsHub:
    """Centralized metrics collection and exposition logic."""

    @staticmethod
    def capture_system_telemetry() -> None:
        """Captures hardware-level telemetry once per scrape."""
        try:
            CPU_USAGE.set(psutil.cpu_percent())
            RAM_USAGE.set(psutil.virtual_memory().used)
            VRAM_AVAILABLE.set(8.0 * 1024**3)
        except Exception as exc:
            logger.error("Metrics: telemetry capture drift - %s", exc)

    @staticmethod
    def mission_started() -> None:
        ACTIVE_MISSIONS.inc()

    @staticmethod
    def mission_finished(success: bool, stage: Optional[str] = None) -> None:
        ACTIVE_MISSIONS.dec()
        if success:
            MISSION_COMPLETED.inc()
        else:
            MISSION_ABORTED.inc()
            if stage:
                MISSION_FAILURES.labels(stage=stage).inc()

    @staticmethod
    def observe_wave(size: int, queue_depth: int) -> None:
        WAVE_SIZE.observe(max(size, 0))
        EXECUTOR_QUEUE_DEPTH.set(max(queue_depth, 0))

    @staticmethod
    def observe_dag_depth(depth: int) -> None:
        DAG_DEPTH.observe(max(depth, 0))

    @staticmethod
    def observe_node(agent: str, node_id: str, latency_ms: float) -> None:
        AGENT_LATENCY.labels(agent=agent).observe(max(latency_ms, 0))
        NODE_LATENCY.labels(agent=agent, node_id=node_id).observe(max(latency_ms, 0))

    @staticmethod
    def observe_trace_step(step: str, latency_ms: float) -> None:
        TRACE_STEP_LATENCY.labels(step=step).observe(max(latency_ms, 0))

    @staticmethod
    def set_queue_depth(depth: int) -> None:
        EXECUTOR_QUEUE_DEPTH.set(max(depth, 0))

    @staticmethod
    def set_backpressure(resource: str, active: bool) -> None:
        BACKPRESSURE_ACTIVE.labels(resource=resource).set(1 if active else 0)

    @staticmethod
    def record_tool_call(agent: str) -> None:
        TOOL_CALLS_TOTAL.labels(agent=agent).inc()

    @staticmethod
    def record_token_usage(agent: str, tokens: int) -> None:
        if tokens > 0:
            TOKEN_CONSUMPTION.labels(agent=agent).inc(tokens)

    @staticmethod
    def reject_budget(limit_type: str) -> None:
        TOOL_BUDGET_REJECTIONS.labels(limit_type=limit_type).inc()

    @staticmethod
    def record_alert(alert_type: str, severity: str = "warning", active: bool = True) -> None:
        if active:
            ALERTS_TOTAL.labels(alert_type=alert_type, severity=severity).inc()
        LAST_ALERT_STATE.labels(alert_type=alert_type).set(1 if active else 0)

    @staticmethod
    def get_latest_metrics() -> bytes:
        MetricsHub.capture_system_telemetry()
        return generate_latest()

    @staticmethod
    def get_content_type() -> str:
        return CONTENT_TYPE_LATEST


def record_agent_mission(agent: str, status: str, latency_ms: float, tenant_id: str = "global") -> None:
    """
    Backward-compatible agent mission hook used across the older agent base.
    """
    MetricsHub.observe_node(agent, tenant_id or "global", latency_ms)
    if status != "success":
        MISSION_FAILURES.labels(stage=f"agent:{agent}").inc()
