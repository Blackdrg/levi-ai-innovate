"""
Sovereign Redis Compatibility Proxy.
Redirects all legacy calls to backend.db.redis for unified state management.
"""
from backend.db.redis import (
    get_redis_client,
    get_async_redis_client,
    HAS_REDIS,
    HAS_REDIS_ASYNC,
    cache_json,
    get_cached_json,
    distributed_lock,
    save_conversation_buffered,
    get_conversation,
    incr_daily_ai_spend,
    get_daily_ai_spend,
    get_user_credits,
    check_exact_match,
    store_exact_match,
    incr_failure_count,
    get_failure_count
)

# Mandatory aliases for Cognitive Engine
r = get_redis_client()
cache = r
r_async = get_async_redis_client()

def get_redis_connection():
    return get_redis_client()

class SovereignCache:
    @staticmethod
    def get_client():
        return get_redis_client()
    
    @staticmethod
    def get_async_client():
        return get_async_redis_client()
