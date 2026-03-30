from fastapi import APIRouter, Depends, HTTPException, Request
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
        raise HTTPException(status_code=401, detail="User not authenticated")
    
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
        raise HTTPException(status_code=500, detail="Failed to retrieve memory facts")

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
            raise HTTPException(status_code=404, detail="Fact not found")
        
        if doc.to_dict().get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this memory")
            
        doc_ref.delete()
        return {"status": "success", "message": "Memory successfully forgotten"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting fact {fact_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal deletion error")

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
        raise HTTPException(status_code=500, detail="Failed to wipe memory")
