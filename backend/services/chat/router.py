# backend/services/chat/router.py
"""
Sovereign Chat Service Router (v7 Unification).
Legacy entry point redirected to the production-grade LeviBrain engine.
"""
from fastapi import APIRouter, Depends

from backend.auth import get_current_user_optional
from backend.api.chat import conversational_stream_endpoint, conversational_endpoint
from backend.core.orchestrator_types import ChatMessage

router = APIRouter(prefix="", tags=["Legacy Chat"])

@router.post("")
async def legacy_chat_endpoint(request: ChatMessage, identity = Depends(get_current_user_optional)):
    """Bridges legacy service calls to the v7 Chat API."""
    return await conversational_endpoint(request, identity)

@router.post("/stream")
async def legacy_chat_stream_endpoint(request: ChatMessage, identity = Depends(get_current_user_optional)):
    """Bridges legacy streaming calls to the v7 Chat API."""
    return await conversational_stream_endpoint(request, identity)
