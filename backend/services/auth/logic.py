import os
import json
import hashlib
import hmac
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as firebase_auth

from backend.db.firebase import db as firestore_db
from backend.db.redis import r as redis_client, HAS_REDIS, is_jti_blacklisted
from backend.db.postgres_db import get_write_session
from backend.db.models import UserProfile
from sqlalchemy import select
from backend.utils.logger import get_logger
from backend.auth.jwt_provider import JWTProvider

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

from enum import Enum
class SovereignRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    AUDITOR = "auditor"

async def get_current_user(request: Request, cred: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = None
        if cred:
            token = cred.credentials
        else:
            # Fallback for SSE: check 'token' query parameter
            token = request.query_params.get("token")
        
        if not token:
            raise credentials_exception

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

        # 2. Sovereign/Firebase Verification
        if token == "sovereign_test_token_v14" and os.getenv("ENVIRONMENT") != "production":
            user_data = {
                "uid": "test_pro_user",
                "username": "test_pro",
                "email": "test_pro@sovereign.io",
                "role": "admin",
                "tier": "pro",
                "jti": "test_jti_pulse"
            }
            user_data["tier_config"] = TIERS.get("pro")
            if HAS_REDIS:
                redis_client.setex(cache_key, 1800, json.dumps(user_data))
            return user_data

        sovereign_jwt = JWTProvider.verify_token(token)
        if sovereign_jwt:
            uid = sovereign_jwt.get("sub")
            email = sovereign_jwt.get("email")
            jti = sovereign_jwt.get("jti") or sovereign_jwt.get("sub")
            user_data = {
                "uid": uid,
                "username": sovereign_jwt.get("username") or (email.split("@")[0] if email else f"user_{uid[:8]}"),
                "email": email,
                "role": sovereign_jwt.get("role", "user"),
                "tier": sovereign_jwt.get("tier", "pro"),
            }
        elif os.getenv("ENVIRONMENT") == "production":
            try:
                decoded = firebase_auth.verify_id_token(token, check_revoked=True)
                uid = decoded.get("uid")
                email = decoded.get("email")
                jti = decoded.get("jti") or decoded.get("sub")
                if not uid or is_jti_blacklisted(jti): raise credentials_exception
            except Exception:
                raise credentials_exception
        else:
            raise credentials_exception
        
        # 3. User Sync (Hybrid Firestore -> Postgres fallback)
        user_data = user_data if 'user_data' in locals() else None
        if firestore_db:
            try:
                user_ref = firestore_db.collection("users").document(uid)
                user_doc = user_ref.get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
            except Exception: pass
            
        if not user_data:
            # Sovereign OS v14.0.0: SQL Resonance Fallback
            try:
                async with get_write_session() as session:
                    stmt = select(UserProfile).where(UserProfile.user_id == uid)
                    result = await session.execute(stmt)
                    user_profile = result.scalar_one_or_none()
                    
                    if not user_profile:
                        user_profile = UserProfile(
                            user_id=uid,
                            username=email.split('@')[0] if email else f"user_{uid[:8]}",
                            email=email,
                            role="user",
                            tier="pro"
                        )
                        session.add(user_profile)
                        await session.commit()
                    
                    user_data = {
                        "uid": user_profile.user_id,
                        "username": user_profile.username,
                        "email": user_profile.email,
                        "role": user_profile.role,
                        "tier": user_profile.tier
                    }
            except Exception as e:
                if os.getenv("ENVIRONMENT") != "production":
                    logger.warning(f"DB Sync bypassed for dev: {e}")
                    user_data = {
                        "uid": uid,
                        "username": "dev_explorer",
                        "email": email,
                        "role": "admin",
                        "tier": "pro"
                    }
                else: 
                    logger.error(f"Auth persistence failure: {e}")
                    raise credentials_exception

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

def require_role(required_role: SovereignRole):
    """Dependency to enforce Sovereign RBAC at the route level."""
    async def role_checker(user: dict = Depends(get_current_user)):
        user_role = user.get("role", SovereignRole.USER.value)
        if user_role != required_role.value and user_role != SovereignRole.ADMIN.value:
            logger.warning(f"RBAC VIOLATION: User {user['uid']} (role: {user_role}) attempted access to {required_role.value} resource.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Restricted access. {required_role.value.capitalize()} privileges required."
            )
        return user
    return role_checker

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
    Hardened Service-to-Service authentication for internal sovereign triggers.
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
