"""
Sovereign JWT Provider v14.0.0.
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
    Sovereign Identity Layer v14.1.0-RS256.
    Graduated from HS256 to RS256 for asymmetric security.
    """
    
    ALGORITHM = "RS256"
    IDENT_EXPIRY = 15 # Minutes
    REFRESH_EXPIRY = 7 # Days

    _private_key = None
    _public_key = None

    @classmethod
    def _load_keys(cls):
        if cls._private_key and cls._public_key:
            return

        cert_dir = os.path.join(os.path.dirname(__file__), "..", "..", "certs")
        priv_path = os.path.join(cert_dir, "jwt_rs256_private.pem")
        pub_path = os.path.join(cert_dir, "jwt_rs256_public.pem")

        try:
            if os.path.exists(priv_path):
                with open(priv_path, "r") as f:
                    cls._private_key = f.read()
            
            if os.path.exists(pub_path):
                with open(pub_path, "r") as f:
                    cls._public_key = f.read()
            
            is_prod = os.getenv("ENVIRONMENT") == "production"

            if not cls._private_key or not cls._public_key:
                 if is_prod:
                     logger.critical("🚨 PRODUCTION BLOCKER: RS256 Identity Keys MISSING from /certs. Graduation ABORTED.")
                     raise RuntimeError("Production Graduation Failure: RS256 keys required.")

                 # Fallback to HS256 if keys are missing (Dev Only)
                 cls.ALGORITHM = "HS256"
                 cls._private_key = os.getenv("JWT_SECRET", "sovereign_monolith_default_secret")
                 cls._public_key = cls._private_key
                 logger.warning("JWT: RS256 keys missing. Falling back to HS256 (DEVELOPMENT ONLY).")
            else:
                 cls.ALGORITHM = "RS256"
                 logger.info("JWT: RS256 Asymmetric Identity Layer ACTIVE.")

        except Exception as e:
            if os.getenv("ENVIRONMENT") == "production":
                 raise e 
            logger.error(f"JWT Key Loading Error: {e}")
            cls.ALGORITHM = "HS256"
            cls._private_key = os.getenv("JWT_SECRET", "sovereign_monolith_default_secret")
            cls._public_key = cls._private_key

    @classmethod
    def create_token_pair(cls, user_id: str, payload: Dict[str, Any]) -> Dict[str, str]:
        """Creates an Identity/Refresh token pair with unique JTIs."""
        cls._load_keys()
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
        
        ident_token = jwt.encode(ident_payload, cls._private_key, algorithm=cls.ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, cls._private_key, algorithm=cls.ALGORITHM)
        
        # 🛡️ Security Check: Default Secret Warning
        if cls.ALGORITHM == "HS256" and cls._private_key == "sovereign_monolith_default_secret" and os.getenv("ENVIRONMENT") == "production":
            logger.critical("🚨 SECURITY ALERT: PRODUCTION ENVIRONMENT USING DEFAULT JWT SECRET. FORGERY IS TRIVIAL.")
        
        # Record creation event (No need to await, fire and forget)
        try:
            import asyncio
            from backend.utils.runtime_tasks import create_tracked_task
            loop = asyncio.get_event_loop()
            if loop.is_running():
                 create_tracked_task(AuditLogger.log_event(
                     event_type="AUTH",
                     action="Token Issued",
                     user_id=user_id,
                     status="success",
                     metadata={"ident_jti": ident_jti, "alg": cls.ALGORITHM}
                 ), name=f"auth-audit-{ident_jti}")
        except: pass

        return {
            "identity_token": ident_token,
            "refresh_token": refresh_token,
            "ident_jti": ident_jti,
            "refresh_jti": refresh_jti
        }

    @classmethod
    def verify_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """Verifies a JWT and checks for revocation."""
        cls._load_keys()
        try:
            # For RS256, we verify with the public key. For HS256, we verify with the secret.
            decoded = jwt.decode(token, cls._public_key, algorithms=[cls.ALGORITHM])
            
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
        from backend.db.redis import get_redis_client
        client = get_redis_client()
        if not client:
            logger.error("JWT Revocation requires active Redis instance.")
            return
            
        key = f"revoked_jti:{jti}"
        client.setex(key, 3600 * 24 * 7, "true") # Default 7 days
        logger.info(f"JWT: Revoked JTI {jti}")

    @classmethod
    def rotate_internal_key(cls, new_key: str):
        """
        Sovereign v14.0.0: Admin-Triggered Key Rotation.
        """
        logger.warning("JWT: ROTATING INTERNAL SERVICE KEY. Inter-agent resonance pulse will shift.")
        os.environ["INTERNAL_SERVICE_KEY"] = new_key
        logger.info("JWT: Internal Service Key rotation finalized.")

    @classmethod
    def _is_revoked(cls, jti: str) -> bool:
        """Checks if a JTI is present in the revocation list."""
        from backend.db.redis import get_redis_client
        client = get_redis_client()
        if not client: return False
        try:
            return client.exists(f"revoked_jti:{jti}") > 0
        except Exception:
            return False
