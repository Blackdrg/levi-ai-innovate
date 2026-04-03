"""
Sovereign Memory API v8.
Strategic management of the FAISS-powered Sovereign Vault and Knowledge Graph.
Bridges to VectorDB and SovereignVault for encrypted semantic recall.
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field

from backend.api.utils.auth import get_current_user
from backend.db.vector_store import VectorDB
from backend.utils.encryption import SovereignVault
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Memory V8"])

class MemorySaveRequest(BaseModel):
    fact: str = Field(..., description="Fact to crystallize in the vault")
    category: str = "general"
    importance: float = 0.8

class QueryRequest(BaseModel):
    query: str = Field(..., description="Semantic query for recall")

@router.post("/recall")
async def semantic_recall_endpoint(
    request: QueryRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Performs a high-fidelity semantic recall from the Sovereign Vault (V8).
    Decrypts results at rest if they are identity-level traits.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    logger.info(f"[Memory-V8] Semantic recall for {user_id}")
    
    try:
        memory_db = await VectorDB.get_user_collection(user_id, "memory")
        results = await memory_db.search(request.query, limit=10)
        
        # Also check traits collection (encrypted)
        traits_db = await VectorDB.get_user_collection(user_id, "traits")
        trait_results = await traits_db.search(request.query, limit=5)
        
        decrypted_traits = []
        for t in trait_results:
            try:
                # Decrypt if it looks like a Vault-encrypted string
                plain = SovereignVault.decrypt(t["text"])
                decrypted_traits.append({"text": plain, "type": "trait", "score": t.get("score")})
            except:
                decrypted_traits.append({"text": t["text"], "type": "trait", "score": t.get("score")})

        return {
            "query": request.query,
            "episodic": results,
            "semantic_traits": decrypted_traits,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"[Memory-V8] Recall failure: {e}")
        raise HTTPException(status_code=500, detail="Neural recall anomaly.")

@router.post("/crystallize")
async def crystallize_memory_endpoint(
    request: MemorySaveRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Manually crystallizes a fact into the Sovereign archive (V8).
    Supports category-based routing (Episodic vs Semantic).
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    logger.info(f"[Memory-V8] Crystallizing pattern for {user_id}")
    
    try:
        if request.category == "trait":
            # Encrypt identity-level traits
            db = await VectorDB.get_user_collection(user_id, "traits")
            content = SovereignVault.encrypt(request.fact)
        else:
            db = await VectorDB.get_user_collection(user_id, "memory")
            content = request.fact
            
        await db.add([content], [{"category": request.category, "timestamp": str(datetime.now())}])
        
        return {"status": "crystallized", "vault": "sovereign_v8"}
    except Exception as e:
        logger.error(f"[Memory-V8] Crystallization failure: {e}")
        raise HTTPException(status_code=500, detail="Crystallization sequence failed.")
