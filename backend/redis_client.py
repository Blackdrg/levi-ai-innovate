
import redis

import os

import json

from dotenv import load_dotenv



load_dotenv()



REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

HAS_REDIS = False

_memory_cache = {}



try:

    r = redis.from_url(REDIS_URL)

    r.ping()

    HAS_REDIS = True

except Exception as e:

    is_missing = "localhost" in REDIS_URL

    masked = REDIS_URL.split("@")[-1] if "@" in REDIS_URL else REDIS_URL

    if is_missing:

        print(f"[Redis] REDIS_URL not set, using in-memory fallback. ({e})")

    else:

        print(f"[Redis] Unavailable at {masked}: {e}. Using in-memory fallback.")





def _get(key):

    if HAS_REDIS:

        return r.get(key)

    return _memory_cache.get(key)





def _set(key, value, ex=None):

    if HAS_REDIS:

        r.set(key, value, ex=ex)

    else:

        _memory_cache[key] = value





def cache_quote_embedding(quote_id: int, embedding: list):

    _set(f"quote:{quote_id}:emb", json.dumps(embedding))





from typing import Any, cast

def get_cached_embedding(quote_id: int):
    raw = _get(f"quote:{quote_id}:emb")
    if not raw:
        return None
    # Redis might return bytes, json.loads expects str/bytes
    return json.loads(cast(Any, raw))


def get_conversation(session_id: str) -> list:
    raw = _get(f"conv:{session_id}")
    if not raw:
        return []
    return json.loads(cast(Any, raw))





def save_conversation(session_id: str, conversation: list):

    _set(f"conv:{session_id}", json.dumps(conversation), ex=3600)





def cache_search(query_hash: str, results: list, ttl: int = 3600):

    _set(f"search:{query_hash}", json.dumps(results), ex=ttl)





def get_cached_search(query_hash: str):
    raw = _get(f"search:{query_hash}")
    if not raw:
        return None
    return json.loads(cast(Any, raw))





def incr_topic(topic: str):

    if HAS_REDIS:

        r.zincrby("popular_topics", 1, topic)





def get_popular_topics(top_k: int = 5, ttl: int = 3600):

    if HAS_REDIS:

        r.expire("popular_topics", ttl)

        return r.zrevrange("popular_topics", 0, top_k - 1, withscores=True)

    return []





def incr_quote_view(quote_hash: str):

    if HAS_REDIS:

        r.zincrby("popular_quotes", 1, quote_hash)





def get_popular_quotes(top_k: int = 5):

    if HAS_REDIS:

        r.expire("popular_quotes", 3600)

        return r.zrevrange("popular_quotes", 0, top_k - 1, withscores=True)

    return []

def store_jti(jti: str, expires_in: int):
    """Store JTI in Redis with expiration."""
    _set(f"jti:{jti}", "1", ex=expires_in)

def is_jti_blacklisted(jti: str) -> bool:
    """Check if JTI is NOT in Redis (we use whitelist pattern for active tokens).
    Wait, the user said 'Add a jti stored in Redis on issue. On every authenticated request, check the jti exists in Redis.'
    So it's a whitelist.
    """
    return _get(f"jti:{jti}") is None

def delete_jti(jti: str):
    """Remove JTI from Redis (revocation)."""
    if HAS_REDIS:
        r.delete(f"jti:{jti}")
    elif f"jti:{jti}" in _memory_cache:
        del _memory_cache[f"jti:{jti}"]

