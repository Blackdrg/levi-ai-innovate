"""
Sovereign Search API v8.
Directed factual retrieval and research for the LEVI-AI OS.
Refactored to V8 Sovereign standard.
"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field

from backend.api.utils.auth import get_current_user
from backend.core.v8.executor import GraphExecutor
from backend.core.v8.meta_planner import MetaPlanner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Search V8"])

class SearchRequest(BaseModel):
    query: str = Field(..., description="The factual search query")
    session_id: Optional[str] = None

@router.post("")
async def search_endpoint(
    payload: SearchRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    Direct Search Interface (V8).
    Bridges to the GraphExecutor for research_agent execution.
    """
    user_id = current_user.uid if hasattr(current_user, "uid") else "guest"
    logger.info(f"[Search-V8] Factual mission for {user_id}")
    
    try:
        # We force a 'research' intent or use the meta-planner
        planner = MetaPlanner()
        # In a real search, we might just call the search agent directly, 
        # but V8 prefers Graph orchestration.
        graph = await planner.plan(f"Deep search and provide facts on: {payload.query}", user_id=user_id)
        
        executor = GraphExecutor()
        perception = {
            "user_id": user_id,
            "session_id": payload.session_id or "search_session",
            "input": payload.query,
            "context": {"intent": "search"}
        }
        
        results = await executor.run(graph, perception)
        
        # Pull the primary search result
        final_answer = ""
        for r in results:
            if r.success and r.agent == "research_agent":
                final_answer = r.message
                break
        
        if not final_answer:
            final_answer = " ".join([r.message for r in results if r.success])

        return {
            "query": payload.query,
            "answer": final_answer,
            "orchestrated": True,
            "v8_status": "crystallized"
        }
    except Exception as e:
        logger.error(f"[Search-V8] Research failure: {e}")
        raise HTTPException(status_code=500, detail="Search sequence failure.")
