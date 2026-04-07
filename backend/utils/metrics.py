"""
Sovereign Metrics Hub v14.0.0.
Provides Prometheus-compatible telemetry for system health, VRAM, and missions.
"""

import psutil
import logging
from prometheus_client import Gauge, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

# 1. System Health Metrics
VRAM_AVAILABLE = Gauge('vram_available_bytes', 'Free VRAM available for neural inference')
CPU_USAGE = Gauge('cpu_usage_percent', 'System CPU utilization')
RAM_USAGE = Gauge('ram_usage_bytes', 'System RAM utilization')

# 2. Mission & Agent Metrics
ACTIVE_MISSIONS = Gauge('active_missions', 'Number of currently processing missions')
MISSION_COMPLETED = Counter('missions_completed_total', 'Total successful missions')
MISSION_ABORTED = Counter('missions_aborted_total', 'Total aborted/failed missions')
MISSION_CU = Histogram('mission_cu_consumption', 'Cognitive Units consumed per mission')
COGNITIVE_UNITS_CONSUMED = Counter('cognitive_units_total', 'Total cumulative Cognitive Units consumed')
AGENT_LATENCY = Histogram('agent_latency_ms', 'Agent response latency in milliseconds', ['agent'])
GPU_SEMAPHORE_AVAILABLE = Gauge('gpu_semaphore_available', 'Number of available GPU task slots')

# 3. Store Performance
FAISS_SEARCH_LATENCY = Histogram('faiss_search_ms', 'FAISS semantic search latency')
REDIS_MEMORY = Gauge('redis_memory_bytes', 'Redis memory consumption')

class MetricsHub:
    """Centralized metrics collection and exposition logic."""
    
    @staticmethod
    def capture_system_telemetry():
        """Captures hardware-level telemetry once per scrape."""
        try:
            # CPU/RAM
            CPU_USAGE.set(psutil.cpu_percent())
            RAM_USAGE.set(psutil.virtual_memory().used)
            
            # VRAM (Mocked for local-first systems without NVML, can be hardened with nvidia-smi)
            # Threshold: Alert at 3GB
            VRAM_AVAILABLE.set(8.0 * 1024**3) # Placeholder for real telemetry integration
            
        except Exception as e:
            logger.error(f"Metrics: Telemetry capture drift - {e}")

    @staticmethod
    def get_latest_metrics() -> bytes:
        """Generates the latest metrics payload for the /metrics endpoint."""
        MetricsHub.capture_system_telemetry()
        return generate_latest()

    @staticmethod
    def get_content_type() -> str:
        return CONTENT_TYPE_LATEST
