import logging
from sqlalchemy import select, func
from backend.db.models import MissionMetric
from backend.db.postgres_db import get_read_session
from typing import Dict, Any

logger = logging.getLogger("Sovereign.Analyzer")

async def analyze_execution_metrics() -> Dict[str, Any]:
    """
    Analyzes the Brain Execution Metrics to verify the <40% LLM target.
    Pulls real historical data from the MissionMetric table.
    """
    async with get_read_session() as session:
        stmt = select(
            MissionMetric.intent,
            func.count(MissionMetric.id).label("count"),
            func.avg(MissionMetric.latency_ms).label("avg_latency")
        ).group_by(MissionMetric.intent)
        
        result = await session.execute(stmt)
        rows = result.all()
        
        if not rows:
            return {"status": "silent", "message": "No mission data found."}

        total_missions = sum(row.count for row in rows)
        
        llm_intensive_intents = ["complex_reasoning", "research", "code_generation"]
        llm_count = 0
        internal_count = 0
        
        intent_stats = []
        for row in rows:
            if row.intent in llm_intensive_intents:
                llm_count += row.count
            else:
                internal_count += row.count
            
            intent_stats.append({
                "intent": row.intent,
                "count": row.count,
                "avg_latency": float(row.avg_latency)
            })

        llm_rate = (llm_count / total_missions) * 100
        internal_rate = (internal_count / total_missions) * 100

        return {
            "status": "active",
            "total_missions": total_missions,
            "llm_rate": round(llm_rate, 2),
            "internal_rate": round(internal_rate, 2),
            "intent_distribution": intent_stats,
            "brain_first_compliance": llm_rate < 40
        }
