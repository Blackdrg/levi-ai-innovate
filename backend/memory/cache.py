"""
Sovereign Memory Cache v8.
Handles Redis-based short-term memory and cross-tier caching.
"""

import logging
from typing import List, Dict, Any, Optional
from backend.db.redis_client import get_conversation, save_conversation_buffered, get_cached_json, cache_json

logger = logging.getLogger(__name__)

class MemoryCache:
    """
    LeviBrain v8: Tier 1 (Working Memory).
    Manages session-local context and fast-access JSON caches.
    """

    @staticmethod
    def get_session_history(session_id: str) -> List[Dict[str, Any]]:
        return get_conversation(session_id)

    @staticmethod
    def save_session_history(session_id: str, history: List[Dict[str, Any]], user_id: str = "guest"):
        save_conversation_buffered(session_id, history, user_id=user_id)

    @staticmethod
    def get_cached_context(key: str) -> Optional[Any]:
        return get_cached_json(key)

    @staticmethod
    def set_cached_context(key: str, data: Any, ttl: int = 600):
        cache_json(key, data, ttl=ttl)
