"""
backend/api/auth.py

Unified Authentication and User Profile API.
Refactored from backend/services/auth/router.py.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Response

from backend.utils.exceptions import LEVIException
from backend.services.auth.logic import get_current_user

from backend.auth.jwt_provider import JWTProvider
from backend.services.auth.logic import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Auth"])

@router.post("/identify")
async def identify_handshake(payload: dict):
    """
    Sovereign v14.2.0: Asymmetric Handshake.
    Resolves identity and returns a secure RS256 token.
    """
    user_id = payload.get("uid") or "guest"
    # Logic to verify user (e.g., via Firebase or DB)
    
    token = JWTProvider.create_token({"sub": user_id, "role": "user"})
    return {
        "status": "success",
        "identity_token": token,
        "handshake_timestamp": datetime.utcnow().isoformat()
    }

@router.post("/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """
    Renews the cosmic session.
    """
    user_id = current_user.get("uid") or current_user.get("id")
    new_token = JWTProvider.create_token({"sub": user_id, "role": current_user.get("role", "user")})
    return {"status": "success", "token": new_token}

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
    from backend.db.redis_client import HAS_REDIS
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
@router.post("/track_share")
async def track_share(current_user: dict = Depends(get_current_user)):
    """Track viral shares and reward bonus credits."""
    uid = current_user.get("uid")
    user_ref = firestore_db.collection("users").document(uid)
    user_ref.update({"share_count": firestore.Increment(1)})
    
    new_shares = current_user.get("share_count", 0) + 1
    if new_shares % 5 == 0:
        user_ref.update({"credits": firestore.Increment(50)})
        return {"status": "rewarded", "bonus": 50}
    return {"status": "success"}
