import logging
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime, timedelta

from backend.api.utils.auth import get_current_user
from backend.memory.cache import MemoryCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v8/mobile", tags=["Sovereign Link"])

class PairingToken(BaseModel):
    token: str
    expires_at: datetime
    qr_code_url: Optional[str] = None

class LinkStatus(BaseModel):
    is_linked: bool
    last_active: Optional[datetime] = None
    device_name: Optional[str] = None

@router.post("/link/generate", response_model=PairingToken)
async def generate_pairing_token(current_user: Any = Depends(get_current_user)):
    """
    Generates a short-lived Sovereign Link pairing token for mobile devices.
    """
    user_id = current_user.user_id if hasattr(current_user, "user_id") else "default_user"
    
    # 1. Generate secure random token
    token = secrets.token_urlsafe(16)
    expire_time = datetime.utcnow() + timedelta(minutes=5)
    
    # 2. Store in cache for 5-minute pairing window
    # Key: sovereign_link:token Value: user_id
    MemoryCache.set(f"sovereign_link:{token}", user_id, expire=300)
    
    logger.info(f"[MobileAuth] Generated pairing token for {user_id}: {token[:10]}...")
    
    return PairingToken(
        token=token,
        expires_at=expire_time,
        qr_code_url=f"/api/v8/mobile/qr?token={token}" # Placeholder for QR generation
    )

@router.post("/link/confirm")
async def confirm_pairing(token: str, device_name: str = "Mobile Device"):
    """
    Endpoint for the mobile app to confirm the pairing token and receive a long-lived JWT.
    """
    # 1. Verify token in cache
    user_id = MemoryCache.get(f"sovereign_link:{token}")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pairing token expired or invalid."
        )
        
    # 2. Invalidate token immediately
    MemoryCache.delete(f"sovereign_link:{token}")
    
    # 3. Store permanent link info in User Profile / DB
    # Key: linked_device:user_id Value: device_name
    # For now, we use the cache with no expiration for persistent link
    MemoryCache.set(f"linked_device:{user_id}", device_name)
    
    logger.info(f"[MobileAuth] Successfully linked device '{device_name}' to user {user_id}")
    
    # Note: In production, we'd return a special Mobile-JWT here
    return {
        "status": "linked",
        "user_id": user_id,
        "device_name": device_name,
        "secret": secrets.token_hex(32) # Secret for telemetry signing
    }

@router.get("/status", response_model=LinkStatus)
async def get_link_status(current_user: Any = Depends(get_current_user)):
    """
    Check if a mobile device is currently linked to the user account.
    """
    user_id = current_user.user_id if hasattr(current_user, "user_id") else "default_user"
    device_name = MemoryCache.get(f"linked_device:{user_id}")
    
    return LinkStatus(
        is_linked=device_name is not None,
        device_name=device_name,
        last_active=datetime.utcnow() if device_name else None
    )
