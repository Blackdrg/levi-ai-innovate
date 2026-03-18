import redis
import os
import json
import hashlib

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
try:
    r = redis.from_url(REDIS_URL)
    r.ping()
    HAS_REDIS = True
except Exception as e:
    # Safely mask URL for logs
    masked_url = REDIS_URL.split('@')[-1] if '@' in REDIS_URL else REDIS_URL
    print(f"Warning: Redis not available at {masked_url}. Error: {e}. Falling back to in-memory cache.")
    HAS_REDIS = False
    _memory_cache = {}

def cache_quote_embedding(quote_id: int, embedding: list):
    if HAS_REDIS:
        r.set(f"quote:{quote_id}:emb", json.dumps(embedding))
    else:
        _memory_cache[f"quote:{quote_id}:emb"] = json.dumps(embedding)

def get_cached_embedding(quote_id: int):
    if HAS_REDIS:
        emb_str = r.get(f"quote:{quote_id}:emb")
    else:
        emb_str = _memory_cache.get(f"quote:{quote_id}:emb")
    return json.loads(emb_str) if emb_str else None

def get_conversation(session_id: str):
    if HAS_REDIS:
        conv_str = r.get(f"conv:{session_id}")
    else:
        conv_str = _memory_cache.get(f"conv:{session_id}")
    return json.loads(conv_str) if conv_str else []

def save_conversation(session_id: str, conversation: list):
    if HAS_REDIS:
        r.set(f"conv:{session_id}", json.dumps(conversation), ex=3600)  # 1hr TTL
    else:
        _memory_cache[f"conv:{session_id}"] = json.dumps(conversation)

def cache_search(query_hash: str, results: list, ttl: int = 3600):
    """Cache search results by query hash"""
    if HAS_REDIS:
        r.set(f"search:{query_hash}", json.dumps(results), ex=ttl)
    else:
        _memory_cache[f"search:{query_hash}"] = json.dumps(results)

def get_cached_search(query_hash: str):
    """Get cached search"""
    if HAS_REDIS:
        cached = r.get(f"search:{query_hash}")
    else:
        cached = _memory_cache.get(f"search:{query_hash}")
    return json.loads(cached) if cached else None

def incr_topic(topic: str):
    """Increment topic popularity"""
    if HAS_REDIS:
        r.zincrby("popular_topics", 1, topic)

def get_popular_topics(top_k: int = 5, ttl: int = 3600):
    """Get top topics with TTL cache"""
    if HAS_REDIS:
        r.expire("popular_topics", ttl)
        return r.zrevrange("popular_topics", 0, top_k-1, withscores=True)
    return []

def incr_quote_view(quote_hash: str):
    """Increment quote view count"""
    if HAS_REDIS:
        r.zincrby("popular_quotes", 1, quote_hash)

def get_popular_quotes(top_k: int = 5):
    """Get top quotes"""
    if HAS_REDIS:
        r.expire("popular_quotes", 3600)
        return r.zrevrange("popular_quotes", 0, top_k-1, withscores=True)
    return []
