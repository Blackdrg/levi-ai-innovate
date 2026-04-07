"""
Sovereign Memory API v13.0.0.
Strategic management of the HNSW-powered Cognitive Vault and Logic Fabric.
"""

import logging
import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime

from backend.api.utils.auth import get_current_user
from backend.db.vector_store import VectorDB
from backend.utils.encryption import SovereignVault
from backend.broadcast_utils import SovereignBroadcaster
from backend.db.postgres_db import get_write_session
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Memory v13"])

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
    Performs a high-fidelity semantic recall from the HNSW Cognitive Vault (v13.0.0).
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    logger.info(f"[Memory-v13] HNSW Semantic recall for {user_id}")
    
    try:
        # v13.0: Absolute HNSW Synchrony
        memory_db = await VectorDB.get_user_collection(user_id, "memory")
        results = await memory_db.search(request.query, limit=10)
        
        # Check traits collection (Fully Encrypted)
        traits_db = await VectorDB.get_user_collection(user_id, "traits")
        trait_results = await traits_db.search(request.query, limit=5)
        
        decrypted_traits = []
        for t in trait_results:
            try:
                plain = SovereignVault.decrypt(t["text"])
                decrypted_traits.append({
                    "text": plain, 
                    "type": "trait", 
                    "score": t.get("score")
                })
            except Exception:
                decrypted_traits.append({
                    "text": t["text"], 
                    "type": "trait", 
                    "score": t.get("score")
                })

        return {
            "query": request.query,
            "episodic": results,
            "semantic_traits": decrypted_traits,
            "status": "synchronized_v13"
        }
    except Exception as e:
        logger.error(f"[Memory-v13] Recall sequence failed: {e}")
        raise HTTPException(status_code=500, detail="HNSW recall anomaly.")

@router.post("/crystallize")
async def crystallize_memory_endpoint(
    request: MemorySaveRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Crystallizes a fact into the Sovereign OS v13.0 archive.
    Synchronizes the HNSW vault with the Postgres SQL Logic Fabric.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    logger.info(f"[Memory-v13] Crystallizing pattern for {user_id}")
    
    try:
        # 1. HNSW Vector Storage
        if request.category == "trait":
            db = await VectorDB.get_user_collection(user_id, "traits")
            content = SovereignVault.encrypt(request.fact)
        else:
            db = await VectorDB.get_user_collection(user_id, "memory")
            content = request.fact
            
        await db.add([content], [{"category": request.category, "timestamp": datetime.now().isoformat()}])
        
        # 2. v13.0 SQL Resonance (Intelligence Traits Table)
        try:
            async with get_write_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO intelligence_traits (trait_id, user_id, pattern, significance, created_at)
                        VALUES (:tid, :uid, :pattern, :sig, CURRENT_TIMESTAMP)
                    """),
                    {
                        "tid": f"trait_{uuid.uuid4().hex[:8]}",
                        "uid": user_id,
                        "pattern": request.fact,
                        "sig": request.importance
                    }
                )
        except Exception as e:
            logger.error(f"[Memory-v13] SQL mirroring failed: {e}")

        # 3. Memory Pulse (Telemetry Bridge)
        SovereignBroadcaster.broadcast({
            "type": "MEMORY_CRYSTALLIZATION",
            "category": request.category,
            "session_id": f"mem_{uuid.uuid4().hex[:6]}",
            "message": f"Celestial Memory Established: {request.category.upper()}."
        })

        return {"status": "crystallized", "vault": "sovereign_v13_hnsw"}
    except Exception as e:
        logger.error(f"[Memory-v13] Crystallization failed: {e}")
        raise HTTPException(status_code=500, detail="Crystallization sequence anomaly.")
