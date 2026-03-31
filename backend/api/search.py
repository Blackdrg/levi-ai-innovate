"""
backend/api/search.py

Dedicated Search API for LEVI-AI.
Provides factual retrieval and thematic research.
"""

import logging
import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Request, BackgroundTasks, UploadFile, File
from backend.auth import get_current_user_optional
from backend.services.orchestrator import run_orchestrator
from backend.utils.sanitization import sanitize_input, sanitize_filename
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Search"])

class SearchRequest(BaseModel):
    query: str = Field(..., description="The factual search query")
    session_id: str = Field(default="", description="Optional session tracking")
    context: Optional[dict] = Field(default=None, description="Optional atmospheric context")

@router.post("")
async def search_endpoint(
    request: Request,
    payload: SearchRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Direct Search Interface.
    Forces the 'search' intent within the Brain.
    """
    user_id = current_user.get("uid") if current_user else f"guest:{request.client.host}"
    user_tier = current_user.get("tier", "free") if current_user else "free"
    
    # Sanitization
    payload.query = sanitize_input(payload.query)

    logger.info("Factual Search Request [%s] (Query: %s)", user_id, payload.query[:50])

    # We use the standard run_orchestrator but can hint at the intent 
    # if we modify run_orchestrator to accept an override_intent.
    # 2. Store temporarily
    # safe_name = sanitize_filename(file.filename)
    # unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    # file_path = os.path.join(UPLOAD_DIR, unique_name)
    
    result = await run_orchestrator(
        user_input=payload.query,
        session_id=payload.session_id,
        user_id=str(user_id),
        background_tasks=background_tasks,
        user_tier=user_tier,
        mood="philosophical" # Search usually benefits from factual depth
    )

    return {
        "query": payload.query,
        "answer": result.get("response"),
        "results": result.get("results"), # Raw tool outputs if available
        "request_id": result.get("request_id")
    }

@router.get("")
async def search_get_endpoint(query: str, session_id: str = ""):
    """Convenience GET endpoint for simple searches."""
    # This just redirects to the orchestrator logic
    from backend.services.orchestrator import run_orchestrator
    result = await run_orchestrator(
        user_input=query,
        session_id=session_id,
        user_id="guest_get",
        user_tier="free"
    )
    return {"answer": result.get("response")}
