# pyright: reportMissingImports=false

import redis  # type: ignore

import os

import json

from dotenv import load_dotenv  # type: ignore



load_dotenv()

from backend.firestore_db import db as firestore_db # type: ignore



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
    # 1. Try Redis cache
    raw = _get(f"conv:{session_id}")
    if raw:
        return json.loads(cast(Any, raw))
    
    # 2. Try Firestore
    try:
        doc = firestore_db.collection("conversations").document(session_id).get()
        if doc.exists:
            conv = doc.to_dict().get("history", [])
            # Re-cache in Redis
            _set(f"conv:{session_id}", json.dumps(conv), ex=3600)
            return conv
    except Exception as e:
        print(f"[Firestore] Error loading conversation {session_id}: {e}")
        
    return []

def save_conversation(session_id: str, conversation: list, user_id: str = None):
    # 1. Save to Redis
    _set(f"conv:{session_id}", json.dumps(conversation), ex=3600)
    
    # 2. Save to Firestore for durability
    try:
        firestore_db.collection("conversations").document(session_id).set({
            "session_id": session_id,
            "user_id": user_id,
            "history": conversation,
            "updated_at": os.environ.get("TIMESTAMP", "") # Optional: use real timestamp
        }, merge=True)
    except Exception as e:
        print(f"[Firestore] Error saving conversation {session_id}: {e}")





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
        _memory_cache.pop(f"jti:{jti}", None)


# ── UserMemory caching (TTL = 10 min) ──────────────────────
def cache_user_memory(user_id: int, memory_dict: dict):
    """Cache a UserMemory dict in Redis for 10 minutes."""
    _set(f"usermem:{user_id}", json.dumps(memory_dict), ex=600)


def get_cached_user_memory(user_id: int) -> dict | None:
    """Retrieve cached UserMemory dict. Returns None on miss."""
    raw = _get(f"usermem:{user_id}")
    if not raw:
        return None
    return json.loads(cast(Any, raw))


def invalidate_user_memory(user_id: int):
    """Remove cached UserMemory (e.g. after an update)."""
    if HAS_REDIS:
        r.delete(f"usermem:{user_id}")
    else:
        _memory_cache.pop(f"usermem:{user_id}", None)


# ── Daily AI spend tracking ─────────────────────────────────
from datetime import date as _date

def incr_daily_ai_spend(amount: float = 1.0) -> float:
    """Increment today's AI spend counter. Returns new total."""
    key = f"ai_spend:{_date.today().isoformat()}"
    if HAS_REDIS:
        pipe = r.pipeline()
        pipe.incrbyfloat(key, amount)
        pipe.expire(key, 86400 * 2)  # auto-expire after 2 days
        result = pipe.execute()
        return float(result[0])
    else:
        current = float(_memory_cache.get(key) or 0)
        current += amount
        _memory_cache[key] = str(current)  # type: ignore
        return current


def get_daily_ai_spend() -> float:
    """Get today's accumulated AI spend."""
    key = f"ai_spend:{_date.today().isoformat()}"
    raw = _get(key)
    if raw is None:
        return 0.0
    return float(raw)
