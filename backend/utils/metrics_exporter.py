# backend/utils/metrics_exporter.py
from prometheus_client import Counter, Gauge, Histogram, Summary
import time

# --- Sovereign Metrics Definitions ---

# 1. Mission Metrics
MISSION_COUNT = Counter('levi_mission_total', 'Total number of cognitive missions executed', ['agent', 'status'])
MISSION_LATENCY = Histogram('levi_mission_latency_seconds', 'Latency of mission completion', ['agent'])

# 2. Memory Resonance Metrics
RESONANCE_SCORE = Gauge('levi_memory_resonance_score', 'Epistemic resonance level (0.0 - 1.0)')
CACHE_HIT_RATE = Gauge('levi_cache_hit_rate', 'Redis/T1 cache efficiency')

# 3. Kernel & Hardware Metrics
VRAM_USAGE = Gauge('levi_kernel_vram_saturation', 'NVIDIA VRAM saturation percentage')
CPU_TEMP = Gauge('levi_kernel_cpu_temperature', 'Kernel thermal authority reading (C)')
SIG_SENT = Counter('levi_kernel_signals_total', 'Total signals dispatched by HAL-0', ['signal'])

# 4. Swarm & DCN Metrics
ACTIVE_NODES = Gauge('levi_dcn_active_nodes', 'Number of active nodes in the discovery mesh')
GOSSIP_PROPAGATION = Histogram('levi_dcn_gossip_seconds', 'Time for a pulse to propagate across the mesh')

class MetricsExporter:
    """
    Sovereign v17.5: Advanced Cognitive Observability.
    Instruments the entire stack for Prometheus/Grafana.
    """
    @staticmethod
    def record_mission(agent: str, status: str, latency: float):
        MISSION_COUNT.labels(agent=agent, status=status).inc()
        MISSION_LATENCY.labels(agent=agent).observe(latency)

    @staticmethod
    def update_hardware(vram: float, temp: float):
        VRAM_USAGE.set(vram)
        CPU_TEMP.set(temp)

    @staticmethod
    def record_signal(sig_name: str):
        SIG_SENT.labels(signal=sig_name).inc()

    @staticmethod
    def update_mesh(node_count: int):
        ACTIVE_NODES.set(node_count)

metrics_exporter = MetricsExporter()
