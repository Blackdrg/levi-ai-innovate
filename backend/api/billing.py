import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text, func, select
from backend.db.postgres_db import get_read_session
from backend.db.models import MissionMetric
from backend.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])

@router.get("/usage")
async def get_usage_summary(
    days: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns a summary of token usage and estimated costs for the user.
    """
    user_id = current_user.get("uid") or current_user.get("user_id")
    
    try:
        async with get_read_session() as session:
            # Aggregate stats for the last N days
            query = select(
                func.sum(MissionMetric.token_count).label("total_tokens"),
                func.sum(MissionMetric.cost_usd).label("total_cost"),
                func.count(MissionMetric.id).label("mission_count")
            ).where(
                MissionMetric.user_id == user_id,
                MissionMetric.created_at >= text(f"NOW() - INTERVAL '{days} days'")
            )
            
            res = await session.execute(query)
            stats = res.mappings().first()
            
            # Daily breakdown
            daily_query = select(
                func.date(MissionMetric.created_at).label("day"),
                func.sum(MissionMetric.token_count).label("tokens"),
                func.sum(MissionMetric.cost_usd).label("cost")
            ).where(
                MissionMetric.user_id == user_id,
                MissionMetric.created_at >= text(f"NOW() - INTERVAL '{days} days'")
            ).group_by(func.date(MissionMetric.created_at)).order_by(func.date(MissionMetric.created_at))
            
            daily_res = await session.execute(daily_query)
            history = daily_res.mappings().all()

            return {
                "summary": {
                    "total_tokens": stats["total_tokens"] or 0,
                    "total_cost_usd": stats["total_cost"] or 0.0,
                    "mission_count": stats["mission_count"] or 0,
                    "period_days": days
                },
                "history": history
            }
    except Exception as e:
        logger.error(f"[Billing] Usage query failure: {e}")
        return {"error": "Failed to retrieve billing data."}
