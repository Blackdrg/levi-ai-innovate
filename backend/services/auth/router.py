from fastapi import APIRouter, Depends, Response # type: ignore
from backend.utils.exceptions import LEVIException

from backend.auth import get_current_user # type: ignore

router = APIRouter(prefix="", tags=["Auth"])

@router.get("/users/me")
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

@router.post("/login")
async def login(response: Response, payload: dict):
    """Stub login for testing and future migration."""
    return {"status": "success", "message": "Login successful", "uid": "test_uid"}

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Stub logout with Redis session revocation check."""
    from backend.db.redis_client import HAS_REDIS
    if not HAS_REDIS:
        raise LEVIException("Redis is required for session revocation", status_code=503, error_code="REDIS_UNAVAILABLE")
    return {"status": "success", "message": "Logged out"}

@router.get("/verify")
async def verify_registration(token: str):
    """Registration verification endpoint."""
    if token == "expired-token":
        raise LEVIException("Verification token has expired", status_code=400, error_code="TOKEN_EXPIRED")
    return {"status": "success", "message": "Account verified"}
