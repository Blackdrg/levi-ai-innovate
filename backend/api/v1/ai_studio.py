"""
backend/api/v1/ai_studio.py

Advanced AI Content Modules - Handles specialized content generation (essays, stories, etc.).
Refactored from backend/services/studio/ai_router.py.
"""

import logging
import os
import asyncio

from fastapi import APIRouter, Depends, Request
from backend.utils.exceptions import LEVIException
from backend.core.orchestrator_types import ContentRequest
from backend.auth.logic import get_current_user
from backend.engines.studio.content_logic import generate_content, get_available_types, get_available_tones
from backend.engines.studio.sd_logic import get_available_styles
from backend.db.redis import is_rate_limited, get_daily_ai_spend, incr_daily_ai_spend
from backend.services.payments.logic import use_credits

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["AI Studio"])

@router.get("/types")
async def list_content_types():
    """ Returns all supported AI content categories. """
    return {"types": get_available_types()}

@router.get("/tones")
async def list_content_tones():
    """ Returns all supported AI emotional tones. """
    return {"tones": get_available_tones()}

@router.get("/styles")
async def list_image_styles():
    """ Returns all supported visual styles. """
    return {"styles": get_available_styles()}

@router.post("/generate")
async def gen_content(
    request: Request,
    req: ContentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generates high-fidelity AI content based on category, topic, and tone.
    """
    user_id = current_user.get("uid")
    
    # 1. Protection (Rate Limiting)
    if is_rate_limited(str(user_id), limit=10):
        raise LEVIException("Thought stream saturated. Please wait.", status_code=429)

    # 2. Financials (Credit Check)
    if req.type != "quote":
        try:
            use_credits(str(user_id), 1)
        except LEVIException:
            raise
        except Exception:
            raise LEVIException("Insufficient cosmic energy.", status_code=402)

    # 3. Evolutionary Persona Context (v6.8)
    from backend.services.learning.logic import AdaptivePromptManager
    persona_manager = AdaptivePromptManager(user_id)
    persona_context = await persona_manager.get_system_instructions()
    
    # 4. Global Guard
    daily_limit = float(os.getenv("DAILY_AI_LIMIT", "500"))
    if get_daily_ai_spend() >= daily_limit:
        raise LEVIException("Planetary AI limit reached.", status_code=429)
    
    incr_daily_ai_spend(1.0)

    # 5. Generation with Evolutionary Synthesis
    try:
        result = await asyncio.to_thread(
            generate_content,
            content_type=req.type,
            topic=req.topic,
            tone=req.tone,
            depth=req.depth,
            language=req.language,
            persona_context=persona_context # Pass distilled persona for higher fidelity
        )
        
        if "error" in result:
            raise LEVIException(result["error"], status_code=400)
        
        return result
    except Exception as e:
        logger.error(f"Content generation failure: {e}")
        raise LEVIException("Failed to manifest content.", status_code=500)
