"""
Sovereign Shield Authentication v8.
Unified entry point for v7 (Legacy JWT) and v8 (Firebase) identity systems.
"""

# New v8 logic (Firebase, Firestore, Redis)
from .logic import get_current_user, get_current_user_optional, verify_internal_service

# Legacy v7 logic (JWT, SovereignAuth)
from .legacy import SovereignAuth, UserIdentity, get_sovereign_identity

__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "verify_internal_service",
    "SovereignAuth",
    "UserIdentity",
    "get_sovereign_identity"
]
