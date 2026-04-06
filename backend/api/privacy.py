"""
backend/api/privacy.py

Privacy and Memory Management API - Allows users to view and delete learned facts.
Refactored from backend/services/orchestrator/privacy_router.py.
"""

import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from backend.utils.exceptions import LEVIException
from backend.auth import get_current_user
from backend.db.postgres import PostgresDB
from backend.db.models import UserFact
from backend.core.memory_utils import prune_old_facts
from backend.utils.robustness import standard_retry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Privacy"])

@router.get("")
@router.get("/facts")
async def get_my_facts(current_user: dict = Depends(get_current_user)):
    """
    Returns all personalized facts LEVI has learned about the user.
    """
    user_id = current_user.get("uid") or current_user.get("user_id")
    try:
        from sqlalchemy import select
        async with PostgresDB._session_factory() as session:
            stmt = select(UserFact).where(UserFact.user_id == user_id).order_by(UserFact.created_at.desc())
            result = await session.execute(stmt)
            facts_models = result.scalars().all()
            
            facts = [
                {
                    "id": f.id,
                    "fact": f.fact,
                    "category": f.category,
                    "learned_at": f.created_at.isoformat()
                } for f in facts_models
            ]
            
        return {"user_id": user_id, "facts": facts, "count": len(facts)}
    except Exception as e:
        logger.error(f"Memory retrieval failure: {e}")
        raise LEVIException("Failed to retrieve personalized memory.", status_code=500)

@router.post("/save")
async def save_fact(payload: dict, current_user: dict = Depends(get_current_user)):
    """
    Manually saves a fact to the user's cosmic memory.
    """
    user_id = current_user.get("uid") or current_user.get("user_id")
    fact = payload.get("fact")
    category = payload.get("category", "general")
    
    if not fact:
        raise LEVIException("Fact content is required.", status_code=400)
    
    try:
        async with PostgresDB._session_factory() as session:
            new_fact = UserFact(
                user_id=user_id,
                fact=fact,
                category=category
            )
            session.add(new_fact)
            await session.commit()
            await session.refresh(new_fact)
            return {"status": "success", "message": "Fact crystallized in memory.", "id": new_fact.id}
    except Exception as e:
        logger.error(f"Memory save failure: {e}")
        raise LEVIException("Failed to crystallize memory.", status_code=500)

@router.delete("/facts/{fact_id}")
async def delete_fact(
    fact_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Deletes a specific learned fact from LEVI's memory.
    """
    user_id = current_user.get("uid") or current_user.get("user_id")
    try:
        from sqlalchemy import delete, select
        async with PostgresDB._session_factory() as session:
            # First verify ownership
            stmt = select(UserFact).where(UserFact.id == int(fact_id))
            result = await session.execute(stmt)
            fact_model = result.scalar_one_or_none()
            
            if not fact_model:
                raise LEVIException("Fact not found.", status_code=404)
            
            if fact_model.user_id != user_id:
                raise LEVIException("Unauthorized memory access.", status_code=403)
                
            await session.delete(fact_model)
            await session.commit()
            
        return {"status": "success", "message": "Memory successfully forgotten."}
    except LEVIException:
        raise
    except Exception as e:
        logger.error(f"Memory deletion failure: {e}")
        raise LEVIException("Failed to forget memory.", status_code=500)

@router.delete("/facts/clear-all")
async def clear_all_memory(current_user: dict = Depends(get_current_user)):
    """
    Wipes all learned facts and vector indices for the current user.
    """
    user_id = current_user.get("uid")
    try:
        from backend.core.memory_manager import MemoryManager
        cleared_count = await MemoryManager.clear_all_user_data(user_id)
        
        return {
            "status": "success", 
            "cleared_count": cleared_count, 
            "message": "Sovereign memory purge complete. Zero semantic residue remains."
        }
    except Exception as e:
        logger.error(f"Memory wipe failure: {e}")
        raise LEVIException("Failed to wipe cosmic memory layers.", status_code=500)
