"""
Sovereign Knowledge Graph API v8.
Real-time Relational & Neural Mapping for the LEVI-AI OS.
Bridges to the Neo4j-powered GraphEngine for entity-relation recall.
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field

from backend.api.utils.auth import get_current_user
from backend.memory.graph_engine import GraphEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Knowledge V8"])

class EntityQuery(BaseModel):
    entity: str = Field(..., description="The name of the entity to retrieve relationships for")

class ResonanceQuery(BaseModel):
    query: str = Field(..., description="Natural language query for lateral resonance")

@router.get("/entity/{name}")
async def get_entity_resonance(
    name: str,
    current_user: Any = Depends(get_current_user)
):
    """
    Retrieves all relational triplets linked to a specific entity for the user (V8).
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    logger.info(f"[Knowledge-V8] Entity retrieval: {name} for {user_id}")
    
    try:
        graph = GraphEngine()
        profile = await graph.get_entity_profile(user_id, name)
        
        return {
            "entity": name,
            "relationships": profile.get("relationships", []),
            "status": "synchronized"
        }
    except Exception as e:
        logger.error(f"[Knowledge-V8] Entity retrieval failure: {e}")
        raise HTTPException(status_code=500, detail="Relational neural failure.")

@router.post("/resonance")
async def get_lateral_resonance(
    request: ResonanceQuery,
    current_user: Any = Depends(get_current_user)
):
    """
    Performs 'Lateral Resonance' - finding connected entities across the knowledge graph (V8).
    Enables deep context injection for complex missions.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    logger.info(f"[Knowledge-V8] Lateral resonance for {user_id}")
    
    try:
        graph = GraphEngine()
        results = await graph.get_connected_resonance(user_id, request.query)
        
        return {
            "query": request.query,
            "resonance": results,
            "depth": 1,
            "status": "crystallized"
        }
    except Exception as e:
        logger.error(f"[Knowledge-V8] Resonance failure: {e}")
        raise HTTPException(status_code=500, detail="Cosmic resonance anomaly.")
