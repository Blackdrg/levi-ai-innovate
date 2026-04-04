"""
Sovereign Identity & Access Management v7 (Legacy Bridge).
Renamed to resolve directory conflict while preserving v7 API support.
"""

import os
import logging
import jwt
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# --- Configuration ---
SECRET_KEY = os.getenv("SOVEREIGN_AUTH_SECRET", "default_sovereign_secret_998811")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 Hours

class UserIdentity(BaseModel):
    user_id: str
    role: str = "guest"
    tier: str = "free"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SovereignAuth:
    """
    Identity Engine for the LEVI-AI Sovereign OS.
    Ensures every neural mission is associated with a verified identity.
    """
    
    @staticmethod
    def generate_token(identity: UserIdentity) -> str:
        expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = identity.dict()
        payload.update({"exp": expires})
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> Optional[UserIdentity]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("user_id")
            if user_id is None: return None
            return UserIdentity(**payload)
        except: return None

from fastapi import Request, HTTPException

async def get_sovereign_identity(request: Request) -> UserIdentity:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return UserIdentity(user_id=f"guest_{request.client.host if request.client else 'local'}")
    token = auth_header.split(" ")[1]
    identity = SovereignAuth.verify_token(token)
    if not identity:
        raise HTTPException(status_code=401, detail="Sovereign Identity pulse invalid.")
    return identity
