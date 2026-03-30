from fastapi import APIRouter, Depends, HTTPException, Request
from backend.utils.exceptions import LEVIException
from typing import List, Dict, Any, Optional
import logging

from backend.auth import get_current_user
from backend.firestore_db import db as firestore_db
from .memory_utils import prune_old_facts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Privacy & Memory"])

@router.get("/facts")
async def get_my_facts(
    current_user: dict = Depends(get_current_user)
):
    """View all facts LEVI has learned about you."""
    user_id = current_user.get("uid")
    if not user_id:
        raise LEVIException("User not authenticated", status_code=401, error_code="UNAUTHORIZED")
    
    try:
        # Maintenance: Prune old facts on view
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
        logger.error(f"Error fetching facts for privacy view: {e}")
        raise LEVIException("Failed to retrieve memory facts", status_code=500, error_code="MEMORY_FETCH_FAIL")

@router.delete("/facts/{fact_id}")
async def delete_fact(
    fact_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a specific piece of information LEVI remembers."""
    user_id = current_user.get("uid")
    
    try:
        doc_ref = firestore_db.collection("user_facts").document(fact_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise LEVIException("Fact not found", status_code=404, error_code="ITEM_NOT_FOUND")
        
        if doc.to_dict().get("user_id") != user_id:
            raise LEVIException("Not authorized to delete this memory", status_code=403, error_code="FORBIDDEN")
            
        doc_ref.delete()
        return {"status": "success", "message": "Memory successfully forgotten"}
    except LEVIException:
        raise
    except Exception as e:
        logger.error(f"Error deleting fact {fact_id}: {e}")
        raise LEVIException("Internal deletion error", status_code=500, error_code="MEMORY_DELETE_FAIL")

@router.delete("/facts/clear-all")
async def clear_all_memory(
    current_user: dict = Depends(get_current_user)
):
    """Wipe all learned facts (The 'Fresh Start' command)."""
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
            if count % 400 == 0: # Firestore batch limit
                batch.commit()
                batch = firestore_db.batch()
        
        batch.commit()
        return {"status": "success", "cleared_count": count}
    except Exception as e:
        logger.error(f"Error clearing memory for {user_id}: {e}")
        raise LEVIException("Failed to wipe memory", status_code=500, error_code="MEMORY_CLEAR_FAIL")
