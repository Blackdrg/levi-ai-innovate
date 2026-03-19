import os
import redis
import json

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
HAS_REDIS = False
redis_client = None

# Fallback in-memory storage
_cache = {}
_history = {}

try:
    _client = redis.from_url(REDIS_URL, socket_connect_timeout=2)
    _client.ping()
    redis_client = _client
    HAS_REDIS = True
    print(f"✅ Redis connected: {REDIS_URL}")
except Exception as e:
    print(f"⚠️ Redis unavailable: {e}. Using in-memory fallback.")

def cache_search(query_hash: str, results: list):
    if HAS_REDIS:
        redis_client.setex(f"search:{query_hash}", 3600, json.dumps(results))
    else:
        _cache[query_hash] = results

def get_cached_search(query_hash: str) -> list:
    if HAS_REDIS:
        cached = redis_client.get(f"search:{query_hash}")
        return json.loads(cached) if cached else None
    return _cache.get(query_hash)

def save_conversation(session_id: str, history: list):
    if HAS_REDIS:
        redis_client.setex(f"chat:{session_id}", 3600, json.dumps(history))
    else:
        _history[session_id] = history

def get_conversation(session_id: str) -> list:
    if HAS_REDIS:
        cached = redis_client.get(f"chat:{session_id}")
        return json.loads(cached) if cached else []
    return _history.get(session_id, [])

