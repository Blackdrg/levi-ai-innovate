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

security = HTTPBearer()

async def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = cred.credentials
        # Check Redis cache first
        cache_key = f"user_token:{hashlib.md5(token.encode()).hexdigest()}"
        
        if HAS_REDIS:
            cached_user = redis_client.get(cache_key)
            if cached_user:
                return json.loads(cached_user)

        decoded_token = firebase_auth.verify_id_token(token)
        uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        if not uid: raise credentials_exception
        
        # Firestore-native user lookup
        users_ref = firestore_db.collection("users")
        user_docs = users_ref.where("email", "==", email).limit(1).get(timeout=5)
        
        user_data = None
        user_list = list(user_docs)
        if not user_list:
            # Create user in Firestore if not exists
            base_username = email.split('@')[0] if email else f"user_{uid[:8]}"
            username = base_username
            
            # Check for username uniqueness
            existing_usernames = users_ref.where("username", "==", username).limit(1).get(timeout=5)
            counter = 1
            while list(existing_usernames):
                username = f"{base_username}{counter}"
                existing_usernames = users_ref.where("username", "==", username).limit(1).get(timeout=5)
                counter += 1
            
            user_data = {
                "uid": uid,
                "username": username,
                "email": email,
                "created_at": datetime.utcnow().isoformat(),
                "tier": "free",
                "credits": 10
            }
            users_ref.document(uid).set(user_data)
        else:
            user_doc = user_list[0]
            user_data = user_doc.to_dict()
            user_data["id"] = user_doc.id
            # Convert datetime objects to string for JSON serialization
            for key, value in user_data.items():
                if isinstance(value, datetime):
                    user_data[key] = value.isoformat()

        # Cache in Redis (TTL: 1 hour)
        if HAS_REDIS and user_data:
            redis_client.setex(cache_key, 3600, json.dumps(user_data))

        return user_data
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise credentials_exception

async def get_current_user_optional(cred: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    if not cred: return None
    try:
        decoded_token = firebase_auth.verify_id_token(cred.credentials)
        email = decoded_token.get("email")
        if not email: return None
        
        users_ref = firestore_db.collection("users")
        user_docs = users_ref.where("email", "==", email).limit(1).get()
        if not list(user_docs): return None
        
        user = list(user_docs)[0].to_dict()
        user["id"] = list(user_docs)[0].id
        return user
    except Exception:
        return None

async def verify_admin(request: Request):
    admin_key = os.getenv("ADMIN_KEY", "")
    provided_key = request.headers.get("X-Admin-Key", "")
    if not admin_key or not hmac.compare_digest(provided_key.encode(), admin_key.encode()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized admin access")
    return True
