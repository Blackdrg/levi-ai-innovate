from fastapi import APIRouter, Depends, HTTPException, Request, Response # type: ignore
from typing import Optional
import os

from backend.auth import get_current_user, get_current_user_optional # type: ignore
from backend.payments import use_credits # type: ignore

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

@router.get("/credits")
async def get_user_credits(current_user: dict = Depends(get_current_user)):
    return {"credits": current_user.get("credits", 0), "tier": current_user.get("tier", "free")}

# In a more advanced version, we would add the Razorpay logic here too.
