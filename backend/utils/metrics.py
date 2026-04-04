from prometheus_client import Counter, Histogram, Gauge
import logging

logger = logging.getLogger(__name__)

# --- Sovereign Metrics v13.0.0 ---

# 1. Agent Mission Performance
AGENT_MISSION_TOTAL = Counter(
    'sovereign_agent_mission_total',
    'Total missions processed per agent',
    ['agent', 'status', 'tenant_id']
)

AGENT_MISSION_LATENCY = Histogram(
    'sovereign_agent_mission_latency_ms',
    'Latency of agent missions in milliseconds',
    ['agent', 'tenant_id'],
    buckets=(100, 500, 1000, 2500, 5000, 10000, 30000)
)

# 2. Error Budgets & SLOs
# SLO: 99.9% Success Rate, <2s P95 Latency for core agents
AGENT_ERROR_TOTAL = Counter(
    'sovereign_agent_error_total',
    'Total errors encountered per agent',
    ['agent', 'error_type', 'tenant_id']
)

# 3. System Sovereignty
MEMORY_DISTILLATION_GAUGE = Gauge(
    'sovereign_memory_distillation_score',
    'Fidelity of memory distillation across tiers',
    ['tier']
)

ACTIVE_MISSIONS = Gauge(
    'sovereign_active_missions',
    'Number of concurrent missions in the BrainPulse'
)

# 4. Cognitive Units (CU)
COGNITIVE_UNITS_CONSUMED = Counter(
    'sovereign_cognitive_units_total',
    'Total CUs consumed by missions',
    ['user_id', 'agent']
)

def record_agent_mission(agent: str, status: str, latency_ms: float, tenant_id: str = "global"):
    """
    Standard recording for Sovereign Agent SLOs.
    """
    AGENT_MISSION_TOTAL.labels(agent=agent, status=status, tenant_id=tenant_id).inc()
    AGENT_MISSION_LATENCY.labels(agent=agent, tenant_id=tenant_id).observe(latency_ms)
    
    if status == "error":
        AGENT_ERROR_TOTAL.labels(agent=agent, error_type="generic", tenant_id=tenant_id).inc()

def record_cu_consumption(user_id: str, agent: str, units: float):
    """
    Tracks Cognitive Unit burn rate for billing and limits.
    """
    COGNITIVE_UNITS_CONSUMED.labels(user_id=user_id, agent=agent).inc(units)
