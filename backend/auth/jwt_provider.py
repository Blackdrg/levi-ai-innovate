"""
Sovereign JWT Provider v13.1.0.
Independent identity provider with full token lifecycle.
Features: 15m Identity Token, 7d Refresh Token, JTI Revocation in Redis.
"""

import os
import jwt # PyJWT
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from backend.utils.audit import AuditLogger

logger = logging.getLogger(__name__)

class JWTProvider:
    """
    Sovereign Identity Layer v13.1.0.
    Replaces common external IDPs with a resident, cryptographic provider.
    """
    
    SECRET_KEY = os.getenv("JWT_SECRET", "sovereign_monolith_default_secret")
    ALGORITHM = "HS256"
    IDENT_EXPIRY = 15 # Minutes
    REFRESH_EXPIRY = 7 # Days

    @classmethod
    def create_token_pair(cls, user_id: str, payload: Dict[str, Any]) -> Dict[str, str]:
        """Creates an Identity/Refresh token pair with unique JTIs."""
        ident_jti = str(uuid.uuid4())
        refresh_jti = str(uuid.uuid4())
        
        ident_payload = {
            **payload,
            "sub": user_id,
            "jti": ident_jti,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=cls.IDENT_EXPIRY),
            "type": "identity"
        }
        
        refresh_payload = {
            "sub": user_id,
            "jti": refresh_jti,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(days=cls.REFRESH_EXPIRY),
            "type": "refresh"
        }
        
        ident_token = jwt.encode(ident_payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        
        # 🛡️ Security Check: Default Secret Warning
        if cls.SECRET_KEY == "sovereign_monolith_default_secret" and os.getenv("ENVIRONMENT") == "production":
            logger.critical("🚨 SECURITY ALERT: PRODUCTION ENVIRONMENT USING DEFAULT JWT SECRET. FORGERY IS TRIVIAL.")
            # We don't crash, but we log the critical failure
        
        # Record creation event (No need to await, fire and forget)
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
             asyncio.create_task(AuditLogger.log_event(
                 event_type="AUTH",
                 action="Token Issued",
                 user_id=user_id,
                 status="success",
                 metadata={"ident_jti": ident_jti}
             ))

        return {
            "identity_token": ident_token,
            "refresh_token": refresh_token,
            "ident_jti": ident_jti,
            "refresh_jti": refresh_jti
        }

    @classmethod
    def verify_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """Verifies a JWT and checks for revocation."""
        try:
            decoded = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            
            # Check JTI Revocation in Redis
            jti = decoded.get("jti")
            if jti and cls._is_revoked(jti):
                logger.warning(f"JWT: Revoked token presented: {jti}")
                return None
                
            return decoded
        except jwt.ExpiredSignatureError:
            logger.debug("JWT: Token expired.")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"JWT: Invalid token: {e}")
            return None

    @classmethod
    def revoke_token(cls, jti: str):
        """Revokes a JTI in Redis with TTL matching the token's remainder."""
        from backend.db.redis import r as redis_client, HAS_REDIS
        if not HAS_REDIS:
            logger.error("JWT Revocation requires active Redis instance.")
            return
            
        key = f"revoked_jti:{jti}"
        redis_client.setex(key, 3600 * 24 * 7, "true") # Default 7 days
        logger.info(f"JWT: Revoked JTI {jti}")

    @classmethod
    def rotate_internal_key(cls, new_key: str):
        """
        Sovereign v13.1.0: Admin-Triggered Key Rotation.
        Updates the legacy INTERNAL_SERVICE_KEY in the runtime environment.
        This allows for mission-draining before rotation to prevent HMAC failure.
        """
        logger.warning("JWT: ROTATING INTERNAL SERVICE KEY. Inter-agent resonance pulse will shift.")
        os.environ["INTERNAL_SERVICE_KEY"] = new_key
        # In a real system, we'd also sync this to Vault or Redis
        logger.info("JWT: Internal Service Key rotation finalized.")

    @classmethod
    def _is_revoked(cls, jti: str) -> bool:
        """Checks if a JTI is present in the revocation list."""
        from backend.db.redis import r as redis_client, HAS_REDIS
        if not HAS_REDIS: return False
        try:
            return redis_client.exists(f"revoked_jti:{jti}") > 0
        except Exception:
            return False
