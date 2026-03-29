import os
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request # type: ignore
from backend.models import ContentRequest # type: ignore
from backend.auth import get_current_user_optional # type: ignore
from backend.content_engine import generate_content, get_available_types, get_available_tones # type: ignore
from backend.sd_engine import get_available_styles # type: ignore
from backend.redis_client import is_rate_limited, get_daily_ai_spend, incr_daily_ai_spend # type: ignore
from backend.payments import use_credits # type: ignore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Modules"])

@router.get("/content/types")
async def list_content_types():
    """Return available content types."""
    return {"types": get_available_types()}

@router.get("/content/tones")
async def list_content_tones():
    """Return available content tones."""
    return {"tones": get_available_tones()}

@router.get("/image/styles")
async def list_image_styles():
    """Return available image generation styles."""
    return {"styles": get_available_styles()}

@router.post("/content/generate")
async def gen_content(
    request: Request,
    req: ContentRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Generate AI content based on type, topic, and tone with cost protection."""
    user_id = current_user.get("uid") if current_user else f"guest:{request.client.host}"
    
    # ── Defensive: Rate Limiting ────────────────────────
    if is_rate_limited(str(user_id), limit=5, window=60):
        logger.warning(f"[RateLimit] Throttled user {user_id} in AI Content")
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")

    # ── Financial: Credit Check ─────────────────────────
    if current_user and req.content_type != "quote":
        try:
            use_credits(str(user_id), 1)
        except Exception as e:
            logger.error(f"[AI Content] Credit deduction failed: {e}")
            raise HTTPException(status_code=402, detail="Insufficient credits.")

    # ── Cost Protection Layer ──────────────────────────
    daily_limit = float(os.getenv("DAILY_AI_LIMIT", "500"))
    if get_daily_ai_spend() >= daily_limit:
        raise HTTPException(status_code=429, detail="Daily AI usage limit reached.")
    incr_daily_ai_spend(1.0)

    result = generate_content(
        content_type=req.content_type,
        topic=req.topic,
        tone=req.tone,
        depth=req.depth,
        language=req.language
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result
