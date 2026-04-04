import logging
import statistics
from typing import List, Dict, Any, Optional
from backend.redis_client import cache

logger = logging.getLogger(__name__)

class ModelDriftDetector:
    """
    Sovereign Drift Guard v13.0.0.
    Monitors agent output distribution and fidelity scores for performance regressions.
    """
    
    WINDOW_SIZE = 100 # Last 100 missions
    DRIFT_THRESHOLD_Z = 2.0 # Standard deviations for alert

    @classmethod
    def record_score(cls, score: float, agent: str = "global"):
        """Records a new fidelity score into the rolling window."""
        key = f"drift_scores:{agent}"
        history = json.loads(cache.get(key) or "[]")
        history.append(score)
        
        # Maintain window size
        if len(history) > cls.WINDOW_SIZE:
            history = history[-cls.WINDOW_SIZE:]
            
        cache.set(key, json.dumps(history), ex=604800) # 7 day TTL
        
        if len(history) >= 20:
            cls.check_for_drift(agent, history)

    @classmethod
    def check_for_drift(cls, agent: str, history: List[float]):
        """
        Uses a basic Z-score check to detect significant deviation from the mean.
        """
        if len(history) < 2: return
        
        mean = statistics.mean(history)
        stdev = statistics.stdev(history) if len(history) > 1 else 0.0
        
        current = history[-1]
        if stdev > 0:
            z_score = abs(current - mean) / stdev
            if z_score > cls.DRIFT_THRESHOLD_Z and current < mean:
                logger.warning(
                    f"[DriftGuard] Significant performance drift detected for agent '{agent}'!"
                    f" Current: {current}, Mean: {mean:.3f}, Z: {z_score:.2f}"
                )
                # Emit alert for Prometheus (can be picked up by a Gauge)
                from backend.utils.metrics import MEMORY_DISTILLATION_GAUGE
                MEMORY_DISTILLATION_GAUGE.labels(tier=f"drift_{agent}").set(z_score)

import json
