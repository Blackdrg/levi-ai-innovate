"""
Sovereign Identity & Access Management v7.
Standardized JWT issuance, session hardening, and RBAC for agentic missions.
"""

import os
import logging
import jwt
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from backend.engines.utils.security import SovereignSecurity

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
        """Issues a new JWT for a Sovereign Identity."""
        expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = identity.dict()
        payload.update({"exp": expires})
        
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"[Auth] Identity token issued for {identity.user_id}")
        return token

    @staticmethod
    def verify_token(token: str) -> Optional[UserIdentity]:
        """Verifies a Sovereign JWT and returns the identity context."""
        try:
            # PII Masking on token input (for logs)
            safe_token = f"{token[:5]}...{token[-5:]}"
            logger.info(f"[Auth] Verifying identity pulse: {safe_token}")
            
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("user_id")
            if user_id is None:
                return None
                
            return UserIdentity(**payload)
        except jwt.ExpiredSignatureError:
            logger.warning("[Auth] Identity pulse expired.")
            return None
        except Exception as e:
            logger.error(f"[Auth] Identity verification failure: {e}")
            return None

    @staticmethod
    def get_security_context(identity: UserIdentity) -> Dict[str, Any]:
        """Generates a hardened security context for agentic execution."""
        return {
            "user_id": identity.user_id,
            "role": identity.role,
            "tier": identity.tier,
            "pii_masking": True,
            "injection_protection": True,
            "timestamp": time.time()
        }

from fastapi import Request, HTTPException

async def get_sovereign_identity(request: Request) -> UserIdentity:
    """Dependency to extract and verify the Sovereign Identity pulse."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return UserIdentity(user_id=f"guest_{request.client.host if request.client else 'local'}")
    
    token = auth_header.split(" ")[1]
    identity = SovereignAuth.verify_token(token)
    if not identity:
        raise HTTPException(status_code=401, detail="Sovereign Identity pulse invalid.")
    return identity
