import logging
import time
import os
import psutil
import json
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class SovereignMonitoring:
    """[Priority 1] Production-grade monitoring, logs, and analytics gateway."""
    
    def __init__(self):
        self.log_path = os.path.abspath("backend/logs/prod_analytics.log")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self.start_time = time.time()

    async def log_mission_metrics(self, mission_id: str, fidelity: float, latency: float, agent_count: int):
        """Records mission performance for long-term analytics."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "mission_id": mission_id,
            "fidelity": fidelity,
            "latency_ms": latency,
            "agent_count": agent_count,
            "cpu_load": psutil.cpu_percent(),
            "mem_usage_mb": psutil.Process().memory_info().rss / 1024 / 1024
        }
        
        try:
            with open(self.log_path, "a") as f:
                f.write(f"{json.dumps(entry)}\n")
            logger.info(f"📊 [Monitoring] Metrics logged for {mission_id}. Fidelity: {fidelity}")
        except Exception as e:
            logger.error(f"⚠️ [Monitoring] Failed to write logs: {e}")

monitoring_service = SovereignMonitoring()
