from fastapi import APIRouter, Depends, HTTPException, Request, Response # type: ignore
from typing import Optional
import os

from backend.auth import get_current_user, get_current_user_optional # type: ignore
from backend.payments import use_credits # type: ignore

router = APIRouter(prefix="/auth", tags=["Auth"], version="3.0.0")

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Standardized user profile response (aligned with main monolith).
    """
    return {
        "id": current_user.get("uid"),
        "username": current_user.get("username") or current_user.get("email"),
        "email": current_user.get("email"),
        "tier": current_user.get("tier", "free"),
        "credits": current_user.get("credits", 0),
        "share_count": current_user.get("share_count", 0),
        "created_at": current_user.get("created_at").isoformat() if current_user.get("created_at") and hasattr(current_user.get("created_at"), "isoformat") else None
    }

@router.get("/credits")
async def get_user_credits(current_user: dict = Depends(get_current_user)):
    return {"credits": current_user.get("credits", 0), "tier": current_user.get("tier", "free")}

# In a more advanced version, we would add the Razorpay logic here too.
