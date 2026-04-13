from datetime import datetime, timezone
from typing import Dict, Any, Optional
import pydantic
from backend.db.models import MissionMetric
from backend.db.postgres import PostgresDB

class EvolutionMetric(pydantic.BaseModel):
    mission_id: str
    user_id: str
    tenant_id: Optional[str] = None
    accuracy_score: float = 0.0
    hallucination_rate: float = 0.0
    reasoning_score: float = 0.0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    token_count: int = 0
    status: str = "success"
    metadata: Dict[str, Any] = {}

class SelfMonitor:
    """
    Sovereign Self-Monitoring System (Weeks 25-28).
    Continuously tracks system performance and efficiency.
    """
    def __init__(self):
        self.metrics_history = []

    async def collect_metrics(self, mission_id: str, results: Dict[str, Any], performance: Dict[str, Any]) -> EvolutionMetric:
        """Collect metrics from a mission execution."""
        metric_data = EvolutionMetric(
            mission_id=mission_id,
            user_id=results.get("user_id", "unknown"),
            tenant_id=results.get("tenant_id"),
            accuracy_score=performance.get("accuracy", 1.0),
            hallucination_rate=performance.get("hallucination", 0.0),
            reasoning_score=performance.get("reasoning", 1.0),
            latency_ms=performance.get("latency", 0.0),
            cost_usd=performance.get("cost", 0.0),
            token_count=performance.get("tokens", 0),
            status=results.get("status", "success"),
            metadata=performance.get("metadata", {})
        )
        
        # Persist to database
        try:
            from backend.db.models import EvolutionMetric as DBEvolutionMetric
            async with PostgresDB._session_factory() as session:
                db_metric = DBEvolutionMetric(
                    mission_id=mission_id,
                    accuracy_score=metric_data.accuracy_score,
                    hallucination_rate=metric_data.hallucination_rate,
                    reasoning_score=metric_data.reasoning_score,
                    latency_ms=metric_data.latency_ms,
                    cost_usd=metric_data.cost_usd,
                    status=metric_data.status,
                    metadata_json=metric_data.metadata
                )
                session.add(db_metric)
                await session.commit()
                print(f"✅ Evolution metrics persisted for mission {mission_id}")
        except Exception as e:
            print(f"❌ Failed to persist evolution metrics: {e}")

        # In-memory history for fast stats
        self.metrics_history.append(metric_data)
        
        # Logic to trigger alerts if degradation is detected
        if metric_data.accuracy_score < 0.8:
            await self.handle_degradation(metric_data)
            
        return metric_data

    async def handle_degradation(self, metric: EvolutionMetric):
        """Action to take when performance drops."""
        print(f"ALERT: Performance degradation detected in mission {metric.mission_id}")
        # Could trigger re-tuning or notification

    def get_summary_stats(self) -> Dict[str, float]:
        """Calculate average metrics."""
        if not self.metrics_history:
            return {}
            
        count = len(self.metrics_history)
        return {
            "avg_accuracy": sum(m.accuracy_score for m in self.metrics_history) / count,
            "avg_latency": sum(m.latency_ms for m in self.metrics_history) / count,
            "avg_cost": sum(m.cost_usd for m in self.metrics_history) / count,
            "success_rate": sum(1 for m in self.metrics_history if m.status == "success") / count
        }

# Global singleton
monitor = SelfMonitor()
