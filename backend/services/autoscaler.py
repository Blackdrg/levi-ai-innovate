# backend/services/autoscaler.py
import logging
import os
import requests
from typing import Dict, Any

logger = logging.getLogger("autoscaler")

class SovereignAutoscaler:
    """
    Sovereign v17.5: Distributed Resource Orchestrator.
    Manages node scaling based on mission backlog and hardware backpressure.
    """
    def __init__(self):
        self.min_nodes = int(os.getenv("MIN_NODES", "3"))
        self.max_nodes = int(os.getenv("MAX_NODES", "10"))
        self.target_cpu_util = 0.75
        self.current_nodes = self.min_nodes

    def check_scaling_thresholds(self, metrics: Dict[str, Any]):
        """Logic to decide if scaling up/down is necessary."""
        cpu_load = metrics.get("cpu_load", 0.0)
        backlog_size = metrics.get("mission_backlog", 0)

        if cpu_load > self.target_cpu_util or backlog_size > 50:
            if self.current_nodes < self.max_nodes:
                self.scale_up()
        elif cpu_load < 0.3 and backlog_size == 0:
            if self.current_nodes > self.min_nodes:
                self.scale_down()

    def scale_up(self):
        """Triggers infrastructure expansion (Simulated Cloud Run/K8s call)."""
        self.current_nodes += 1
        logger.info(f" 🚀 [Autoscaler] SCALING UP: Provisioning new compute node. Current nodes: {self.current_nodes}")
        # In production, this would call gcloud or kubectl
    
    def scale_down(self):
        """Triggers infrastructure contraction."""
        self.current_nodes -= 1
        logger.info(f" 📉 [Autoscaler] SCALING DOWN: Terminating idle node. Current nodes: {self.current_nodes}")

autoscaler = SovereignAutoscaler()
