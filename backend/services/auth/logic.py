import os
import json
import hashlib
import hmac
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as firebase_auth

from backend.db.firebase import db as firestore_db
from backend.db.redis import r as redis_client, HAS_REDIS, is_jti_blacklisted
from backend.utils.logger import get_logger

logger = get_logger("auth")

# Tiers and Pricing (Reference from config)
from backend.config.system import TIERS

security = HTTPBearer()

def check_allowance(user_id: str, tier: str, cost: int = 1) -> bool:
    from backend.db.redis import get_daily_ai_spend, get_user_credits
    limit = TIERS.get(tier, TIERS["free"])["daily_limit"]
    spend = get_daily_ai_spend(user_id)
    if spend + cost > limit:
        credits = get_user_credits(user_id)
        if credits < cost: return False
    return True

async def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = cred.credentials
        token_hash = hashlib.md5(token.encode()).hexdigest()
        cache_key = f"auth:user:{token_hash}"
        
        if HAS_REDIS:
            cached = redis_client.get(cache_key)
            if cached:
                user_data = json.loads(cached)
                if is_jti_blacklisted(user_data.get("jti", "")):
                    redis_client.delete(cache_key)
                    raise credentials_exception
                return user_data

        try:
            decoded = firebase_auth.verify_id_token(token, check_revoked=True)
            uid = decoded.get("uid")
            email = decoded.get("email")
            jti = decoded.get("jti") or decoded.get("sub")
            if not uid or is_jti_blacklisted(jti): raise credentials_exception
        except Exception:
            raise credentials_exception
        
        user_ref = firestore_db.collection("users").document(uid)
        user_doc = await asyncio.to_thread(user_ref.get)
        
        if not user_doc.exists:
            user_data = {
                "uid": uid,
                "username": email.split('@')[0] if email else f"user_{uid[:8]}",
                "email": email,
                "created_at": datetime.now(timezone.utc),
                "tier": "free",
                "credits": 10,
                "last_active": datetime.now(timezone.utc)
            }
            await asyncio.to_thread(user_ref.set, user_data)
        else:
            user_data = user_doc.to_dict()
            user_data["uid"] = uid
            await asyncio.to_thread(user_ref.update, {"last_active": datetime.now(timezone.utc)})

        user_data["jti"] = jti
        user_data["tier_config"] = TIERS.get(user_data.get("tier", "free"))

        # Serialization
        for k, v in user_data.items():
            if isinstance(v, datetime): user_data[k] = v.isoformat()

        if HAS_REDIS:
            redis_client.setex(cache_key, 1800, json.dumps(user_data))
        return user_data

    except HTTPException: raise
    except Exception as e:
        logger.error(f"Auth failure: {e}")
        raise credentials_exception

async def get_current_user_optional(cred: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    if not cred: return None
    try: return await get_current_user(cred)
    except: return None

async def verify_admin(request: Request):
    key = os.getenv("ADMIN_KEY", "")
    provided = request.headers.get("X-Admin-Key", "")
    if not key or not hmac.compare_digest(provided.encode(), key.encode()):
        raise HTTPException(status_code=403, detail="Unauthorized admin")
    return True

async def verify_internal_service(request: Request):
    """
    Hardened Service-to-Service authentication for internal monolith triggers.
    Enforces the use of INTERNAL_SERVICE_KEY for background tasks and distillation.
    """
    internal_key = os.getenv("INTERNAL_SERVICE_KEY") or os.getenv("ADMIN_KEY")
    if not internal_key:
        logger.critical("SECURITY ALERT: No Internal Service Key configured. Failing closed.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Security Configuration Error")
        
    provided_key = request.headers.get("X-Internal-Service-Key", "")
    if not hmac.compare_digest(provided_key.encode(), internal_key.encode()):
        logger.warning(f"Unauthorized service-to-service attempt from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Service Token")
    return True

async def verify_system_admin(request: Request):
    """
    Protects critical system probes and deep health checks.
    Requires ADMIN_KEY and enforces a higher security tier.
    """
    admin_key = os.getenv("ADMIN_KEY")
    if not admin_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Admin configuration missing")
        
    provided_key = request.headers.get("X-Admin-Key", "")
    if not hmac.compare_digest(provided_key.encode(), admin_key.encode()):
        logger.warning(f"Unauthorized system admin probe attempt from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to system probes denied")
    return True
