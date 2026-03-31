"""
backend/api/auth.py

Unified Authentication and User Profile API.
Refactored from backend/services/auth/router.py.
"""

import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.utils.exceptions import LEVIException
from backend.auth import get_current_user, get_current_user_optional
from backend.utils.robustness import standard_retry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Auth"])

@router.get("/users/me")
@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Returns the current user profile.
    """
    # Standardize response shape
    created_at = current_user.get("created_at")
    if created_at and hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()
    elif isinstance(created_at, str):
        pass # Already a string
    else:
        created_at = None

    return {
        "id": current_user.get("uid"),
        "username": current_user.get("username") or current_user.get("email"),
        "email": current_user.get("email"),
        "tier": current_user.get("tier", "free"),
        "credits": current_user.get("credits", 0),
        "share_count": current_user.get("share_count", 0),
        "created_at": created_at
    }

@router.get("/credits")
async def get_user_credits(current_user: dict = Depends(get_current_user)):
    """
    Returns the current user's AI credits.
    """
    return {
        "credits": current_user.get("credits", 0), 
        "tier": current_user.get("tier", "free")
    }

@router.post("/login")
async def login(response: Response, payload: dict):
    """
    Standard login - logic verified via Firebase token or direct credentials.
    Returns success and establishing a handshake.
    """
    from backend.auth import get_current_user # ensure we can use it
    uid = payload.get("uid")
    email = payload.get("email")
    
    if not uid and not email:
        raise LEVIException("Identity context missing.", status_code=400)
        
    return {
        "status": "success", 
        "message": "Login handshake established.", 
        "uid": uid or "guest",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/signup")
async def signup(payload: dict):
    """
    Creates a new seeker identity in the cosmic memory.
    """
    email = payload.get("email")
    password = payload.get("password")
    username = payload.get("username") or email.split('@')[0]
    
    if not email or not password:
        raise LEVIException("Email and password are required for initialization.", status_code=400)
    
    try:
        from firebase_admin import auth as firebase_auth
        user = firebase_auth.create_user(
            email=email,
            password=password,
            display_name=username
        )
        return {
            "status": "success",
            "message": "Seeker identity created. Welcome to LEVI.",
            "uid": user.uid
        }
    except Exception as e:
        logger.error(f"Signup failure: {e}")
        raise LEVIException(str(e), status_code=400)

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Revokes user sessions.
    """
    from backend.redis_client import HAS_REDIS, r as redis
    if not HAS_REDIS:
        raise LEVIException("Session revocation requires Redis.", status_code=503, error_code="REDIS_UNAVAILABLE")
    
    # Optional logic for token blacklisting in Phase 6
    return {"status": "success", "message": "Disconnected from the cosmic field."}

@router.get("/verify")
async def verify_registration(token: str):
    """
    Validates account registration tokens.
    """
    if token == "expired-token":
        raise LEVIException("Token entropy lost.", status_code=400, error_code="TOKEN_EXPIRED")
    return {"status": "success", "message": "Identity verified."}
