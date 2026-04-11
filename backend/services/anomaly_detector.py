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
            # 🛡️ Graduation #16: Detecting decaying cognitive performance
            fidelity_stmt = select(MissionMetric.fidelity_score).where(
                MissionMetric.created_at >= datetime.now(timezone.utc) - timedelta(days=1) # 24h baseline
            )
            res = await session.execute(fidelity_stmt)
            scores = [r[0] for r in res.all() if r[0] > 0]
            
            if len(scores) >= 20:
                avg_fidelity = np.mean(scores)
                # Flag missions with > 30% drop from baseline
                low_fidelity_limit = avg_fidelity * 0.7 
                
                check_stmt = select(MissionMetric).where(
                    MissionMetric.fidelity_score < low_fidelity_limit,
                    MissionMetric.created_at >= datetime.now(timezone.utc) - timedelta(minutes=15)
                )
                res = await session.execute(check_stmt)
                outliers = res.scalars().all()
                
                for m in outliers:
                    logger.warning(f"⚠️ [CognitiveDrift] High-fragility mission: {m.mission_id} (Fidelity: {m.fidelity_score:.2f} vs avg {avg_fidelity:.2f})")
                    # Push to FragilityIndex for domain-level tracking
                    from backend.db.models import FragilityIndex
                    domain = m.intent or "unknown"
                    frag_stmt = select(FragilityIndex).where(FragilityIndex.domain == domain)
                    res = await session.execute(frag_stmt)
                    frag = res.scalar_one_or_none()
                    if frag:
                        frag.failure_count += 1
                        frag.last_updated = datetime.now(timezone.utc)
                    else:
                        session.add(FragilityIndex(domain=domain, failure_count=1))
                
                await session.commit()

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
