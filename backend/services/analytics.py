import logging
from typing import Dict, Any
from backend.db.postgres_db import get_write_session
from backend.db.models import MissionMetric

logger = logging.getLogger(__name__)

async def record_mission_metrics(user_id: str, outcome: Dict[str, Any]):
    """
    Saves mission performance and cost metrics to the Sovereign SQL Fabric.
    """
    try:
        async with get_write_session() as session:
            metric = MissionMetric(
                mission_id=outcome.get("request_id", "unknown"),
                user_id=user_id,
                intent=outcome.get("intent", "general"),
                status="success" if outcome.get("success") else "fail",
                token_count=outcome.get("token_count", 0),
                cost_usd=outcome.get("cost_usd", 0.0),
                latency_ms=outcome.get("latency_ms", 0.0)
            )
            session.add(metric)
            # Commit is automatic in get_write_session
        
        logger.info(f"[Analytics] Mission recorded for {user_id}: {outcome.get('request_id')}")
    except Exception as e:
        logger.error(f"[Analytics] Failed to record mission metrics: {e}")
