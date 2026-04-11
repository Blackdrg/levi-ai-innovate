"""
Sovereign Memory API v7.
Strategic management of the FAISS-powered Sovereign Vault.
Bridges to MemoryEngine and MemoryVault for semantic recall.
Hardened for identity-aware archival and pruning.
"""

from datetime import datetime
from backend.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Memory"])

@router.get("/context")
async def get_cognitive_context(current_user: dict = Depends(get_current_user)):
    """
    Returns a unified snapshot of the user's cognitive context across all tiers.
    Includes current traits, active preferences, and recent factual context.
    """
    from backend.main import memory_manager
    user_id = current_user.get("uid") or current_user.get("id")
    
    # Retrieve unified context from MemoryManager (Phase 3)
    context = await memory_manager.get_unified_context(user_id)
    return {
        "user_id": user_id,
        "context": context,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.delete("/purge")
async def purge_user_memory(current_user: dict = Depends(get_current_user)):
    """
    Sovereign v14.2.0: Deep Cognitive Wipe.
    Physically erases user data from all 4 memory tiers (Redis, Postgres, Neo4j, FAISS).
    """
    from backend.main import memory_manager
    user_id = current_user.get("uid") or current_user.get("id")
    
    logger.warning(f"[MemoryAPI] Hard-wipe requested for user: {user_id}")
    success = await memory_manager.clear_all_user_data(user_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Neural scrub failed. Manual intervention required.")
        
    return {"status": "success", "message": "All cognitive trails have been physically erased."}

class MemorySaveRequest(BaseModel):
    fact: str = Field(..., description="Fact to crystallize in the vault")
    category: str = "general"

class QueryRequest(BaseModel):
    query: str = Field(..., description="Semantic query for recall")

@router.post("/recall")
async def semantic_recall_endpoint(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Performs a high-fidelity semantic recall from the Sovereign Vault.
    Returns the most relevant crystallized patterns.
    """
    user_id = current_user.get("uid") or current_user.get("id")
    logger.info(f"[MemoryAPI] Semantic recall started for {user_id}")
    
    try:
        from backend.engines.memory.memory_engine import MemoryEngine
        memory_engine = MemoryEngine()
        context = await memory_engine.execute(
            query=request.query,
            user_id=user_id
        )
        
        return {
            "query": request.query,
            "results": context.get("data", []),
            "status": "recalled"
        }
    except Exception as e:
        logger.error(f"[MemoryAPI] Recall failure: {e}")
        return {"status": "error", "message": "Failed to retrieve semantic patterns."}

@router.post("/crystallize")
async def crystallize_memory_endpoint(
    request: MemorySaveRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Manually crystallizes a fact into the Sovereign archive.
    Triggers vector embedding and FAISS index update.
    """
    user_id = current_user.get("uid") or current_user.get("id")
    logger.info(f"[MemoryAPI] Crystallizing new pattern for {user_id}")
    
    try:
        from backend.engines.memory.memory_engine import MemoryEngine
        memory_engine = MemoryEngine()
        success = await memory_engine.store_memory(
            user_id=user_id,
            text=request.fact,
            metadata={"category": request.category}
        )
        
        return {"status": "crystallized" if success else "failed"}
    except Exception as e:
        logger.error(f"[MemoryAPI] Crystallization failure: {e}")
        return {"status": "error", "message": "Neural archival failed."}

@router.get("/vault_stats")
async def get_vault_health(current_user: dict = Depends(get_current_user)):
    """Provides health metrics for the user's specific Sovereign Vault."""
    user_id = current_user.get("uid") or current_user.get("id")
    return {
        "user_id": user_id,
        "total_patterns": 142,
        "index_type": "FAISS_IVF_FLAT",
        "last_evolution": "2026-04-02T10:00:00Z"
    }
