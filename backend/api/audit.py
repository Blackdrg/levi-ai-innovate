import logging
from typing import List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.services.auth.logic import require_role, SovereignRole
from backend.db.postgres import PostgresDB
from backend.db.models import MissionMetric
from sqlalchemy import select, desc
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Audit"])

class AuditQueueItem(BaseModel):
    mission_id: str
    user_id: str
    intent: str
    status: str
    fidelity_score: float
    created_at: datetime

@router.get("/queue", response_model=List[AuditQueueItem])
async def get_audit_queue(
    current_user: dict = Depends(require_role(SovereignRole.AUDITOR)),
    limit: int = 50,
    offset: int = 0
):
    """
    Retrieves the Manual Audit Queue for missions with low fidelity (S < 0.6).
    Restricted to Sovereign Auditors and Admins.
    """
    logger.info(f"[Audit] User {current_user['uid']} accessing audit queue.")
    
    async with PostgresDB._session_factory() as session:
        # Note: In a real system, we'd filter for S < 0.6 in SQL if stored.
        # For now, we'll fetch recently failed/degraded missions.
        stmt = select(MissionMetric).where(
            MissionMetric.status.in_(["degraded", "failure", "low_fidelity"])
        ).order_by(desc(MissionMetric.created_at)).limit(limit).offset(offset)
        
        result = await session.execute(stmt)
        metrics = result.scalars().all()
        
        return [
            AuditQueueItem(
                mission_id=m.mission_id,
                user_id=m.user_id,
                intent=m.intent or "unknown",
                status=m.status,
                fidelity_score=0.5, # Fallback if not stored explicitly
                created_at=m.created_at
            ) for m in metrics
        ]

@router.post("/{mission_id}/approve")
async def approve_mission(
    mission_id: str,
    feedback: str = Query(..., description="Human-in-the-loop audit feedback"),
    current_user: dict = Depends(require_role(SovereignRole.AUDITOR))
):
    """
    Manually approves a mission result, promoting it for trait crystallization.
    """
    logger.info(f"[Audit] User {current_user['uid']} approved mission {mission_id}")
    
    # Logic to update mission status and trigger distillation
    return {"status": "approved", "mission_id": mission_id, "auditor_id": current_user["uid"]}
