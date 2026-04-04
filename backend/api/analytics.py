import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text, func, select
from backend.db.postgres_db import get_read_session
from backend.db.models import MissionMetric
from backend.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Performance"])

@router.get("/performance")
async def get_performance_metrics(
    days: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns agent performance metrics (success rate, latency).
    """
    user_id = current_user.get("uid") or current_user.get("user_id")
    
    try:
        async with get_read_session() as session:
            # 1. Global Success Rate
            success_query = select(
                MissionMetric.status,
                func.count(MissionMetric.id).label("count")
            ).where(
                MissionMetric.user_id == user_id,
                MissionMetric.created_at >= text(f"NOW() - INTERVAL '{days} days'")
            ).group_by(MissionMetric.status)
            
            success_res = await session.execute(success_query)
            success_stats = {r["status"]: r["count"] for r in success_res.mappings().all()}
            
            total = sum(success_stats.values())
            success_rate = (success_stats.get("success", 0) / total) * 100 if total > 0 else 100.0
            
            # 2. Latency Trends (Avg latency per day)
            latency_query = select(
                func.date(MissionMetric.created_at).label("day"),
                func.avg(MissionMetric.latency_ms).label("avg_latency")
            ).where(
                MissionMetric.user_id == user_id,
                MissionMetric.created_at >= text(f"NOW() - INTERVAL '{days} days'")
            ).group_by(func.date(MissionMetric.created_at)).order_by(func.date(MissionMetric.created_at))
            
            latency_res = await session.execute(latency_query)
            latency_history = latency_res.mappings().all()

            # 3. Intent Distribution (Which agents are used most)
            intent_query = select(
                MissionMetric.intent,
                func.count(MissionMetric.id).label("count")
            ).where(
                MissionMetric.user_id == user_id,
                MissionMetric.created_at >= text(f"NOW() - INTERVAL '{days} days'")
            ).group_by(MissionMetric.intent).order_by(func.count(MissionMetric.id).desc())
            
            intent_res = await session.execute(intent_query)
            intents = intent_res.mappings().all()

            return {
                "performance": {
                    "success_rate": round(success_rate, 2),
                    "total_missions": total,
                    "avg_latency_ms": round(sum(h["avg_latency"] for h in latency_history) / len(latency_history), 2) if latency_history else 0.0
                },
                "latency_history": latency_history,
                "intent_distribution": intents
            }
    except Exception as e:
        logger.error(f"[Analytics] Performance query failure: {e}")
        return {"error": "Failed to retrieve performance metrics."}
