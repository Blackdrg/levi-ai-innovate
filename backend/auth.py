# backend/auth.py
import os
import json
import uuid
import time
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Any, Dict

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth as firebase_auth

from backend.firestore_db import db as firestore_db
from backend.redis_client import r as redis_client, HAS_REDIS
from backend.utils.retries import logger

from backend.config import TIERS, COST_MATRIX

# Module-level bearer scheme instance — must be defined before get_current_user
# references it via Depends(security).
security = HTTPBearer()

def check_allowance(user_id: str, tier: str, cost: int = 1) -> bool:
    """Verifies if the user has enough daily units or credits."""
    from backend.redis_client import get_daily_ai_spend, get_user_credits # type: ignore
    
    # 1. Check Tier Daily Allowance
    limit = TIERS.get(tier, TIERS["free"])["daily_limit"]
    spend = get_daily_ai_spend(user_id)
    
    if spend + cost > limit:
        # 2. Fallback to purchased credits if daily limit is hit
        credits = get_user_credits(user_id)
        if credits < cost:
            return False
            
    return True


async def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)):
    """Phase 4: Robust Firebase Auth Middleware."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = cred.credentials
        
        # 1. Distributed Cache Lookup
        token_hash = hashlib.md5(token.encode()).hexdigest()
        cache_key = f"auth:user:{token_hash}"
        
        if HAS_REDIS:
            cached_user = redis_client.get(cache_key)
            if cached_user:
                user_data = json.loads(cached_user)
                # Phase 4: JTI Blacklist check even on cache hit
                from backend.redis_client import is_jti_blacklisted
                jti = user_data.get("jti")
                if jti and is_jti_blacklisted(jti):
                     redis_client.delete(cache_key) # Clear invalid cache
                     raise credentials_exception
                return user_data

        # 2. Firebase Verification
        try:
            decoded_token = firebase_auth.verify_id_token(token, check_revoked=True)
            uid = decoded_token.get("uid")
            email = decoded_token.get("email")
            jti = decoded_token.get("jti") or decoded_token.get("sub") # sub is often used as JTI proxy in Firebase
            
            # Phase 4: JTI Blacklist verification
            from backend.redis_client import is_jti_blacklisted
            if jti and is_jti_blacklisted(jti):
                raise credentials_exception
                
            if not uid: raise credentials_exception
        except Exception as fe:
            logger.warning(f"Firebase token verification failed: {fe}")
            raise credentials_exception
        
        # 3. User Synchronization
        user_ref = firestore_db.collection("users").document(uid)
        user_doc = user_ref.get(timeout=5.0)
        
        if not user_doc.exists:
            base_username = email.split('@')[0] if email else f"user_{uid[:8]}"
            user_data = {
                "uid": uid,
                "username": base_username,
                "email": email,
                "created_at": datetime.utcnow(),
                "tier": "free",
                "credits": 10,
                "last_active": datetime.utcnow()
            }
            user_ref.set(user_data)
        else:
            user_data = user_doc.to_dict()
            user_data["uid"] = uid
            user_ref.update({"last_active": datetime.utcnow()})

        # Inject JTI for cache-level blacklisting
        user_data["jti"] = jti

        # Inject Tier Config
        user_data["tier_config"] = TIERS.get(user_data.get("tier", "free"))

        # 4. JSON Serialization Cleanup
        for key, value in user_data.items():
            if isinstance(value, datetime):
                user_data[key] = value.isoformat()

        if HAS_REDIS:
            redis_client.setex(cache_key, 1800, json.dumps(user_data))

        return user_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Critical Auth System Failure: {e}")
        raise credentials_exception

async def get_current_user_optional(cred: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    if not cred: return None
    try:
        return await get_current_user(cred)
    except Exception:
        return None


async def verify_admin(request: Request):
    admin_key = os.getenv("ADMIN_KEY", "")
    provided_key = request.headers.get("X-Admin-Key", "")
    if not admin_key or not hmac.compare_digest(provided_key.encode(), admin_key.encode()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized admin access")
    return True
