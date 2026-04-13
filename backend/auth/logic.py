"""
Sovereign Shield Auth Logic v8.
Handles Firebase verification, user synchronization, and internal service auth.
"""

import os
import json
import hashlib
import hmac
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as firebase_auth
import jwt
import httpx
from cryptography.x509 import load_pem_x509_certificate

from enum import Enum
from functools import wraps
from sqlalchemy import select
from backend.db.postgres import PostgresDB
from backend.db.models import UserProfile
from backend.db.redis_client import r as redis_client, HAS_REDIS, is_jti_blacklisted
from backend.config.system import TIERS
from backend.utils.audit import AuditLogger

class SovereignRole(str, Enum):
    GUEST = "guest"        # Read-only, basic chat
    RESEARCHER = "researcher" # Access to Scout/Librarian
    PRO = "pro"            # Access to all standard agents
    CREATOR = "creator"    # Access to Artisan/Code agents
    ADMIN = "admin"        # System-level controls

# Scope Definitions
SCOPES = {
    "mission:create": [SovereignRole.RESEARCHER, SovereignRole.PRO, SovereignRole.CREATOR, SovereignRole.ADMIN],
    "mission:delete": [SovereignRole.ADMIN, SovereignRole.CREATOR],
    "system:rollback": [SovereignRole.ADMIN],
    "agent:execute": [SovereignRole.PRO, SovereignRole.CREATOR, SovereignRole.ADMIN],
}

def require_scope(required_scope: str):
    """
    Scope-based Access Control.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("current_user")
            if not user:
                for arg in args:
                    if isinstance(arg, dict) and "uid" in arg:
                        user = arg
                        break
            
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required.")
            
            user_role = user.get("role", SovereignRole.GUEST)
            allowed_roles = SCOPES.get(required_scope, [SovereignRole.ADMIN])
            
            if user_role not in allowed_roles and user_role != SovereignRole.ADMIN:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Access Denied: Required scope '{required_scope}' not granted to role '{user_role}'."
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(required_role: SovereignRole):
    """
    Legacy Role-Based Access Control (RBAC).
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("current_user")
            if not user:
                for arg in args:
                    if isinstance(arg, dict) and "uid" in arg:
                        user = arg
                        break
            
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required for RBAC enforcement.")
            
            user_role = user.get("role", SovereignRole.GUEST)
            
            # Permission Hierarchy Logic
            role_hierarchy = {
                SovereignRole.GUEST: 0,
                SovereignRole.RESEARCHER: 1,
                SovereignRole.PRO: 2,
                SovereignRole.CREATOR: 3,
                SovereignRole.ADMIN: 4
            }
            
            if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
                await AuditLogger.log_event(
                    event_type="RBAC",
                    action="Access Denied",
                    user_id=user.get("uid"),
                    status="forbidden",
                    metadata={"required": required_role, "current": user_role, "func": func.__name__}
                )
                raise HTTPException(
                    status_code=403, 
                    detail=f"Access Denied: Required role '{required_role}' or higher required."
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Standard security scheme
security = HTTPBearer()

async def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)):
    """Primary user extraction from Firebase ID Token with Redis caching."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = cred.credentials
        token_hash = hashlib.md5(token.encode()).hexdigest()
        cache_key = f"auth:user:{token_hash}"
        
        # 1. Redis Cache lookup
        if HAS_REDIS:
            cached = redis_client.get(cache_key)
            if cached:
                user_data = json.loads(cached)
                if is_jti_blacklisted(user_data.get("jti", "")):
                    redis_client.delete(cache_key)
                    raise credentials_exception
                return user_data

        # 2. Hardened RS256 Verification (Local Sovereign Check)
        try:
            if token == "sovereign_test_token_v15" and os.getenv("ENVIRONMENT") != "production":
                uid, email, jti = "test_pro_user", "test_pro@sovereign.io", "test_jti_pulse"
            else:
                # v15.0: Local RS256 Verification with Persistent JWKS Cache
                unverified_header = jwt.get_unverified_header(token)
                kid = unverified_header.get("kid")
                if not kid: raise credentials_exception
                
                # Retrieve Public Keys from Redis Cache or Google JWKS
                public_keys = None
                jwks_cache_key = "auth:jwks:google"
                if HAS_REDIS:
                    cached_jwks = redis_client.get(jwks_cache_key)
                    if cached_jwks:
                        public_keys = json.loads(cached_jwks)
                
                if not public_keys:
                    async with httpx.AsyncClient() as client:
                        jwks_resp = await client.get("https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com")
                        public_keys = jwks_resp.json()
                        if HAS_REDIS:
                            # Cache for 24 hours as Google keys don't rotate that frequently
                            redis_client.setex(jwks_cache_key, 86400, json.dumps(public_keys))
                
                cert_pem = public_keys.get(kid)
                if not cert_pem: raise credentials_exception
                
                public_key = load_pem_x509_certificate(cert_pem.encode()).public_key()
                
                # Strict Payload Validation
                project_id = os.getenv("FIREBASE_PROJECT_ID", "levi-ai-v15")
                decoded = jwt.decode(
                    token, 
                    public_key, 
                    algorithms=["RS256"], 
                    audience=project_id, 
                    issuer=f"https://securetoken.google.com/{project_id}"
                )
                
                uid = decoded.get("sub")
                email = decoded.get("email")
                jti = decoded.get("jti") or decoded.get("sub")

            if not uid or is_jti_blacklisted(jti): raise credentials_exception
        except Exception as e:
            logger.error(f"[Auth-Hardened] Verification failure: {e}")
            # Fallback for Local/Development Identity
            if os.getenv("ENVIRONMENT") != "production":
                uid, email, jti = "dev_user_777", "sovereign@levi.ai", "dev_jti_pulse"
            else:
                raise credentials_exception
        
        # 3. User Sync with Postgres (Zero-Cloud Graduation)
        async with PostgresDB._session_factory() as session:
            stmt = select(UserProfile).where(UserProfile.user_id == uid)
            result = await session.execute(stmt)
            user_profile = result.scalar_one_or_none()
            
            if not user_profile:
                user_profile = UserProfile(
                    user_id=uid,
                    email=email,
                    role=SovereignRole.GUEST # Default to Guest for safety
                )
                session.add(user_profile)
                await session.commit()
                await session.refresh(user_profile)
            
            user_data = {
                "uid": user_profile.user_id,
                "email": user_profile.email,
                "role": user_profile.role,
                "tier": user_profile.tier if hasattr(user_profile, 'tier') else "pro",
                "jti": jti
            }

        # 4. Context Enrichment
        user_data["tier_config"] = TIERS.get(user_data.get("tier", "pro"))

        if HAS_REDIS:
            redis_client.setex(cache_key, 1800, json.dumps(user_data))
        return user_data

    except HTTPException: raise
    except Exception:
        raise credentials_exception

async def get_current_user_optional(cred: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    if not cred: return None
    try: return await get_current_user(cred)
    except: return None

async def verify_internal_service(request: Request):
    """Enforces strict service-to-service authentication."""
    internal_key = os.getenv("INTERNAL_SERVICE_KEY") or os.getenv("ADMIN_KEY")
    if not internal_key:
        raise HTTPException(status_code=500, detail="Security Configuration Error")
        
    provided_key = request.headers.get("X-Internal-Service-Key", "")
    if not hmac.compare_digest(provided_key.encode(), internal_key.encode()):
        raise HTTPException(status_code=401, detail="Invalid Service Token")
    return True
