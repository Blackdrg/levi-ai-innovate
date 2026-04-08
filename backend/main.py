"""
Compatibility gateway for the designated backend application entrypoint.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from backend.api.main import app
from backend.auth import get_current_user, get_current_user_optional
from backend.core.orchestrator_types import _INJECTION_PATTERNS
from backend.db.redis_client import HAS_REDIS, r as redis_client


def broadcast_activity(event: str, data: Dict[str, Any]) -> bool:
    """
    Backward-compatible activity broadcaster used by legacy tests and routes.
    """
    payload = json.dumps({"event": event, "data": data})
    if HAS_REDIS and redis_client:
        redis_client.publish("levi_activity", payload)
        return True
    return False


__all__ = [
    "app",
    "broadcast_activity",
    "get_current_user",
    "get_current_user_optional",
    "HAS_REDIS",
    "redis_client",
    "_INJECTION_PATTERNS",
]
