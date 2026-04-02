"""
Sovereign Shield Auth Logic v8.
Handles Firebase verification, user synchronization, and internal service auth.
"""

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

from backend.db.firestore_db import db as firestore_db
from backend.db.redis_client import r as redis_client, HAS_REDIS, is_jti_blacklisted
from backend.config.system import TIERS

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

        # 2. Firebase Verification
        try:
            decoded = firebase_auth.verify_id_token(token, check_revoked=True)
            uid = decoded.get("uid")
            email = decoded.get("email")
            jti = decoded.get("jti") or decoded.get("sub")
            if not uid or is_jti_blacklisted(jti): raise credentials_exception
        except Exception:
            raise credentials_exception
        
        # 3. User Sync with Firestore
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

        # 4. Context Enrichment
        user_data["jti"] = jti
        user_data["tier_config"] = TIERS.get(user_data.get("tier", "free"))

        # Serialization for Redis
        for k, v in user_data.items():
            if isinstance(v, datetime): user_data[k] = v.isoformat()

        if HAS_REDIS:
            redis_client.setex(cache_key, 1800, json.dumps(user_data))
        return user_data

    except HTTPException: raise
    except Exception as e:
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
