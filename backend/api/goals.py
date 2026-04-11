from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from backend.auth import get_current_user
from backend.core.goal_engine import goal_engine
from backend.db.postgres import PostgresDB
from backend.db.models import Goal
from sqlalchemy import select

router = APIRouter(prefix="/goals", tags=["Sovereign Goals"])

class CreateGoalRequest(BaseModel):
    objective: str
    priority: float = 1.0

@router.post("")
async def create_goal(request: CreateGoalRequest, current_user: dict = Depends(get_current_user)):
    """Creates a new long-term sovereign goal."""
    user_id = current_user.get("uid") or current_user.get("id")
    goal_id = await goal_engine.create_persistent_goal(user_id, request.objective, request.priority)
    return {"status": "created", "goal_id": goal_id}

@router.get("")
async def list_goals(current_user: dict = Depends(get_current_user)):
    """Lists all goals for the current user."""
    user_id = current_user.get("uid") or current_user.get("id")
    async with await PostgresDB.get_session() as session:
        stmt = select(Goal).where(Goal.user_id == user_id).order_by(Goal.created_at.desc())
        res = await session.execute(stmt)
        goals = res.scalars().all()
        return goals

@router.get("/{goal_id}")
async def get_goal(goal_id: str, current_user: dict = Depends(get_current_user)):
    """Returns detailed status and decomposition of a specific goal."""
    user_id = current_user.get("uid") or current_user.get("id")
    async with await PostgresDB.get_session() as session:
        stmt = select(Goal).where(Goal.goal_id == goal_id, Goal.user_id == user_id)
        res = await session.execute(stmt)
        goal = res.scalar_one_or_none()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found.")
        
        # Include missions and sub-goals in the response via relationships
        # (Assuming eager loading or simple property access works here)
        return {
            "goal_id": goal.goal_id,
            "objective": goal.objective,
            "status": goal.status,
            "progress": goal.progress,
            "sub_goals": [sg.goal_id for sg in goal.sub_goals],
            "missions": [m.mission_id for m in goal.missions]
        }
