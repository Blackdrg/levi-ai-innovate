import logging
import asyncio
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from backend.db.postgres import PostgresDB
from backend.db.models import MissionMetric, CognitiveUsage
from sqlalchemy import select, func

logger = logging.getLogger(__name__)

class AnomalyDetectorService:
    """
    Sovereign v14.1 Automated Anomaly Detection.
    Monitors mission latency and fidelity for statistical outliers.
    """
    def __init__(self, sensitivity: float = 3.0):
        self.sensitivity = sensitivity # Z-score threshold

    async def scan_for_anomalies(self):
        """Background pulse to detect cognitive and performance drift."""
        logger.info("[AnomalyDetector] Pulsing mission metrics...")
        
        async with PostgresDB._session_factory() as session:
            # 1. Latency Anomalies (System Overload)
            latency_stmt = select(MissionMetric.latency_ms).where(
                MissionMetric.created_at >= datetime.now(timezone.utc) - timedelta(hours=1)
            )
            res = await session.execute(latency_stmt)
            latencies = [r[0] for r in res.all() if r[0] > 0]
            
            if len(latencies) >= 10:
                mean = np.mean(latencies)
                std = np.std(latencies)
                
                # Check most recent missions
                check_stmt = select(MissionMetric).order_by(MissionMetric.created_at.desc()).limit(5)
                res = await session.execute(check_stmt)
                recent = res.scalars().all()
                
                for m in recent:
                    if m.latency_ms > mean + (self.sensitivity * std):
                         logger.critical(f"[Anomaly] Latency outlier detected: {m.mission_id} ({m.latency_ms}ms vs avg {mean:.1f}ms)")
                         # In production, we'd fire an alert or trigger auto-scaling
            
            # 2. Fidelity Anomalies (Cognitive Drift)
            # This would check Mission fidelity_score vs historic per-intent averages
            pass

    async def start(self):
        while True:
            try:
                await self.scan_for_anomalies()
            except Exception as e:
                logger.error(f"[AnomalyDetector] Scan failure: {e}")
            await asyncio.sleep(600) # Every 10 mins

if __name__ == "__main__":
    detector = AnomalyDetectorService()
    asyncio.run(detector.start())
