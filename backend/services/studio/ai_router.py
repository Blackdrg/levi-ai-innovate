from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
from backend.models import ContentRequest
from backend.auth import get_current_user, get_current_user_optional
from backend.content_engine import generate_content, get_available_types, get_available_tones
from backend.sd_engine import get_available_styles

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
    req: ContentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate AI content based on type, topic, and tone."""
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
