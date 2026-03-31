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
from backend.firestore_db import db as firestore_db
from backend.services.orchestrator.memory_utils import prune_old_facts
from backend.utils.robustness import standard_retry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Privacy"])

@router.get("/facts")
async def get_my_facts(current_user: dict = Depends(get_current_user)):
    """
    Returns all personalized facts LEVI has learned about the user.
    """
    user_id = current_user.get("uid")
    try:
        # Maintenance: Prune facts older than 30 days
        await prune_old_facts(user_id)
        
        docs = firestore_db.collection("user_facts") \
            .where("user_id", "==", user_id) \
            .order_by("created_at", direction="DESCENDING") \
            .stream()
            
        facts = []
        for doc in docs:
            data = doc.to_dict()
            facts.append({
                "id": doc.id,
                "fact": data.get("fact"),
                "category": data.get("category"),
                "learned_at": data.get("created_at")
            })
            
        return {"user_id": user_id, "facts": facts, "count": len(facts)}
    except Exception as e:
        logger.error(f"Memory retrieval failure: {e}")
        raise LEVIException("Failed to retrieve personalized memory.", status_code=500)

@router.delete("/facts/{fact_id}")
async def delete_fact(
    fact_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Deletes a specific learned fact from LEVI's memory.
    """
    user_id = current_user.get("uid")
    try:
        doc_ref = firestore_db.collection("user_facts").document(fact_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise LEVIException("Fact not found.", status_code=404)
        
        if doc.to_dict().get("user_id") != user_id:
            raise LEVIException("Unauthorized memory access.", status_code=403)
            
        doc_ref.delete()
        return {"status": "success", "message": "Memory successfully forgotten."}
    except LEVIException:
        raise
    except Exception as e:
        logger.error(f"Memory deletion failure: {e}")
        raise LEVIException("Failed to forget memory.", status_code=500)

@router.delete("/facts/clear-all")
async def clear_all_memory(current_user: dict = Depends(get_current_user)):
    """
    Wipes all learned facts for the current user.
    """
    user_id = current_user.get("uid")
    try:
        docs = firestore_db.collection("user_facts") \
            .where("user_id", "==", user_id) \
            .stream()
            
        count = 0
        batch = firestore_db.batch()
        for doc in docs:
            batch.delete(doc.reference)
            count += 1
            if count % 400 == 0:
                batch.commit()
                batch = firestore_db.batch()
        
        batch.commit()
        return {"status": "success", "cleared_count": count, "message": "Fresh start initiated."}
    except Exception as e:
        logger.error(f"Memory wipe failure: {e}")
        raise LEVIException("Failed to wipe cosmic memory.", status_code=500)
