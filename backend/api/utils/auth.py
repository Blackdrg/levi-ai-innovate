"""
backend/api/utils/auth.py
Unified API-level Authentication Utilities.
Re-exports from backend/services/auth/logic to maintain backward compatibility (v13.0 Bridge).
"""
from backend.services.auth.logic import (
    get_current_user,
    get_current_user_optional,
    require_role,
    SovereignRole,
    verify_admin,
    verify_internal_service,
    verify_system_admin
)
