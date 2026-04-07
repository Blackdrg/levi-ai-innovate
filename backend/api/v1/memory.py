"""
Sovereign Memory API v7.
Strategic management of the FAISS-powered Sovereign Vault.
Bridges to MemoryEngine and MemoryVault for semantic recall.
Hardened for identity-aware archival and pruning.
"""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.auth.logic import get_current_user as get_sovereign_identity
from backend.auth.models import UserProfile as UserIdentity
from backend.memory.manager import MemoryManager
from backend.utils.audit import AuditLogger
from backend.db.vector import get_vector_index

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Memory"])

# Initialize production memory components
# Initialize v8 memory manager
memory_manager = MemoryManager()

class MemorySaveRequest(BaseModel):
    fact: str = Field(..., description="Fact to crystallize in the vault")
    category: str = "general"

class ErasureRequest(BaseModel):
    record_id: str = Field(..., description="ID of the record to erase/forget")
    collection: str = "memory"

class QueryRequest(BaseModel):
    query: str = Field(..., description="Semantic query for recall")

# Dependency removed as we use get_current_user from auth.logic

@router.post("/recall")
async def semantic_recall_endpoint(
    request: QueryRequest,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Performs a high-fidelity semantic recall from the Sovereign Vault.
    Returns the most relevant crystallized patterns.
    """
    logger.info(f"[MemoryAPI] Semantic recall started for {identity.uid}")
    
    try:
        # Retrieve context from the engine (bridged in Phase 1)
        res = await memory_manager.get_long_term(
            user_id=identity.uid,
            query=request.query
        )
        
        return {
            "query": request.query,
            "results": res.get("preferences", []) + res.get("traits", []) + res.get("history", []),
            "status": "recalled"
        }
    except Exception as e:
        logger.error(f"[MemoryAPI] Recall failure: {e}")
        return {"status": "error", "message": f"Failed to retrieve semantic patterns: {str(e)}"}

@router.post("/crystallize")
async def crystallize_memory_endpoint(
    request: MemorySaveRequest,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Manually crystallizes a fact into the Sovereign archive.
    Triggers vector embedding and FAISS index update.
    """
    logger.info(f"[MemoryAPI] Crystallizing new pattern for {identity.uid}")
    
    try:
        from backend.memory.vector_store import SovereignVectorStore
        await SovereignVectorStore.store_fact(
            user_id=identity.uid,
            fact=request.fact,
            category=request.category,
            importance=0.8
        )
        
        return {"status": "crystallized"}
    except Exception as e:
        logger.error(f"[MemoryAPI] Crystallization failure: {e}")
        return {"status": "error", "message": "Neural archival failed."}

@router.post("/erasure")
async def gdpr_erasure_endpoint(
    request: ErasureRequest,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Sovereign v13.1.0: Managed GDPR Erasure Protocol.
    Marks a vector for immediate deletion and records an audit trail.
    """
    logger.info(f"[MemoryAPI] GDPR Erasure requested for {identity.uid} (ID: {request.record_id})")
    
    try:
        # 1. Audit Request Entry
        await AuditLogger.log_event(
            event_type="GDPR",
            action="Erasure Request",
            user_id=identity.uid,
            resource_id=request.record_id,
            metadata={"collection": request.collection}
        )

        # 2. Execute soft-delete
        index = await get_vector_index(identity.uid, request.collection)
        await index.delete(request.record_id)
        
        return {"status": "erased", "record_id": request.record_id}
    except Exception as e:
        logger.error(f"[MemoryAPI] Erasure failure: {e}")
        await AuditLogger.log_event(
            event_type="GDPR",
            action="Erasure Failed",
            user_id=identity.uid,
            resource_id=request.record_id,
            status="failed",
            metadata={"error": str(e)}
        )
        return {"status": "error", "message": "Neural erasure failed."}

@router.get("/vault_stats")
async def get_vault_health(identity: UserIdentity = Depends(get_sovereign_identity)):
    """Provides health metrics for the user's specific Sovereign Vault."""
    # Simulation for v7 metrics
    return {
        "user_id": identity.user_id,
        "total_patterns": 142,
        "index_type": "FAISS_IVF_FLAT",
        "last_evolution": "2026-04-02T10:00:00Z"
    }
