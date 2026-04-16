"""
backend/monitoring/prometheus.py
LEVI-AI Sovereign OS v16.2.0 — Phase 4.2: Comprehensive Monitoring

Prometheus metrics for tracking mission lifecycle, cognitive fidelity,
and hardware resource utilization.
"""

from prometheus_client import Counter, Histogram, Gauge, Summary

# --- Mission Metrics ---

mission_counter = Counter(
    'levi_missions_total',
    'Total missions processed by the Orchestrator',
    ['status'] # e.g. success, failed, timeout
)

mission_latency = Summary(
    'levi_mission_duration_seconds',
    'Time spent processing a mission'
)

# --- Cognitive Metrics ---

fidelity_histogram = Histogram(
    'levi_fidelity_score',
    'Mission fidelity distribution as judged by the Reflection Engine',
    buckets=(0.0, 0.25, 0.50, 0.75, 0.85, 0.90, 0.95, 1.0)
)

intent_drift_gauge = Gauge(
    'levi_intent_drift',
    'Measured drift in intent classification anchors'
)

# --- Hardware & Kernel Metrics ---

vram_gauge = Gauge(
    'levi_vram_usage_mb',
    'Current VRAM usage across all agents',
    ['node_id']
)

process_count = Gauge(
    'levi_active_processes',
    'Total number of isolated kernel tasks'
)

# --- DCN & Consensus Metrics ---

raft_term_gauge = Gauge(
    'levi_raft_current_term',
    'Current Raft consensus term',
    ['cluster']
)

gossip_nodes_gauge = Gauge(
    'levi_dcn_active_nodes',
    'Number of active nodes in the DCN gossip mesh'
)

def record_mission(status: str, fidelity: float = 1.0):
    """Utility to record mission outcome and fidelity."""
    mission_counter.labels(status=status).inc()
    if fidelity is not None:
        fidelity_histogram.observe(fidelity)

def update_vram(node_id: str, usage_mb: float):
    """Update VRAM gauge with latest kernel telemetry."""
    vram_gauge.labels(node_id=node_id).set(usage_mb)
