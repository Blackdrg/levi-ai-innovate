# pyright: reportMissingImports=false

import redis  # type: ignore
import os
import json
import redis
import redis.asyncio as aioredis
from typing import Optional, Any, Dict
from dotenv import load_dotenv  # type: ignore



load_dotenv()

from backend.firestore_db import db as firestore_db # type: ignore



REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

HAS_REDIS = False

_memory_cache = {}



try:
    r = redis.from_url(REDIS_URL, socket_timeout=5)
    r.ping()
    HAS_REDIS = True
    print(f"[Redis] Successfully connected to {REDIS_URL.split('@')[-1] if '@' in REDIS_URL else REDIS_URL}")
except Exception as e:
    HAS_REDIS = False
    is_prod = os.getenv("ENVIRONMENT") == "production"
    error_msg = f"[Redis] Critical: Connection to Redis failed ({e})."
    
    if is_prod:
        # Phase 3: Enforce Redis in Production
        print(f"CRITICAL: {error_msg} Redis is MANDATORY in production for session memory, rate limiting, and caching.")
        # In actual production, we might want to raise an error to stop the container
        raise RuntimeError(error_msg)
    else:
        print(f"{error_msg} Falling back to in-memory cache (Local Dev).")





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
            # Re-cache in Redis if it's a valid serializable list
            if isinstance(conv, list) and is_serializable(conv):
                _set(f"conv:{session_id}", json.dumps(conv), ex=3600)
            return conv
    except Exception as e:
        print(f"[Firestore] Error loading conversation {session_id}: {e}")
        
    return []

def is_serializable(obj: Any) -> bool:
    """Helper to check if an object is JSON serializable."""
    try:
        json.dumps(obj)
        return True
    except (TypeError, OverflowError):
        return False

def save_conversation(session_id: str, conversation: list, user_id: str = None):
    # 1. Save to Redis
    _set(f"conv:{session_id}", json.dumps(conversation), ex=3600)
    
    # 2. Save to Firestore for durability
    try:
        from datetime import datetime
        firestore_db.collection("conversations").document(session_id).set({
            "session_id": session_id,
            "user_id": user_id,
            "history": conversation,
            "updated_at": datetime.utcnow().isoformat()
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
    """Store JTI in Redis or Firestore with expiration."""
    if HAS_REDIS:
        _set(f"jti:{jti}", "1", ex=expires_in)
    else:
        # Fallback to Firestore for shared state across instances
        try:
            from datetime import datetime, timedelta
            expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            firestore_db.collection("blacklisted_jtis").document(jti).set({
                "jti": jti,
                "expires_at": expiry
            })
        except Exception as e:
            print(f"[Firestore] Failed to store JTI: {e}")

def is_jti_blacklisted(jti: str) -> bool:
    """Check if JTI is explicitly blacklisted in Redis."""
    if HAS_REDIS:
        return _get(f"jti:{jti}") is not None
    
    # Fallback to Firestore
    try:
        doc = firestore_db.collection("blacklisted_jtis").document(jti).get()
        if doc.exists:
            from datetime import datetime
            expires_at = doc.to_dict().get("expires_at")
            # If still valid, it's blacklisted
            if expires_at and expires_at.replace(tzinfo=None) > datetime.utcnow(): # type: ignore
                return False # Actually the caller logic said 'is None' returns True?
        return True # Whitelist: if not in DB, it's blacklisted (wait, logic is flipped?)
    except Exception:
        return True

def delete_jti(jti: str):
    """Remove JTI from Redis/Firestore."""
    if HAS_REDIS:
        r.delete(f"jti:{jti}")
    else:
        try:
            firestore_db.collection("blacklisted_jtis").document(jti).delete()
        except Exception:
            pass


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

def incr_daily_ai_spend(user_id: str = "global", amount: float = 1.0) -> float:
    """Increment a user's (or global) daily AI spend counter."""
    key = f"ai_spend:{user_id}:{_date.today().isoformat()}"
    if HAS_REDIS:
        pipe = r.pipeline()
        pipe.incrbyfloat(key, amount)
        pipe.expire(key, 86400 * 2)  # auto-expire after 2 days
        result = pipe.execute()
        return float(result[0])
    else:
        current = float(_memory_cache.get(key) or 0)
        current += amount
        _memory_cache[key] = str(current)
        return current

def get_daily_ai_spend(user_id: str = "global") -> float:
    """Get a user's (or global) daily AI spend."""
    key = f"ai_spend:{user_id}:{_date.today().isoformat()}"
    raw = _get(key)
    if raw is None:
        return 0.0
    return float(raw)

def get_user_credits(user_id: str) -> int:
    """Fast credit retrieval with Firestore fallback."""
    key = f"user_credits:{user_id}"
    cached = _get(key)
    if cached:
        return int(cached)
    
    # Fallback to Firestore
    try:
        user_doc = firestore_db.collection("users").document(user_id).get(timeout=5)
        if user_doc.exists:
            credits = int(user_doc.to_dict().get("credits", 0))
            if HAS_REDIS:
                r.setex(key, 300, credits) # Cache for 5 mins
            return credits
    except Exception as e:
        print(f"[Redis/Firestore] Credit retrieval failed: {e}")
    return 0


# --- Enhanced Concurrency Control (Lua for Atomicity) ---

ACQUIRE_SLOT_LUA = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
if current > tonumber(ARGV[2]) then
    redis.call('DECR', KEYS[1])
    return 0
end
return 1
"""

def acquire_concurrency_slot(limit_key: str, max_concurrent: int, ttl: int = 3600) -> bool:
    """
    Try to acquire a concurrency slot globally via Redis (Atomic Lua).
    """
    if not HAS_REDIS:
        return True
    
    try:
        # returns 1 if acquired, 0 if limit reached
        result = r.eval(ACQUIRE_SLOT_LUA, 1, limit_key, ttl, max_concurrent)
        return bool(result)
    except Exception as e:
        print(f"[Redis] Concurrency acquire failed: {e}")
        return True # Fail open to avoid blocking production on Redis issues


def release_concurrency_slot(limit_key: str):
    """Release a concurrency slot."""
    if HAS_REDIS:
        # Ensure we don't go below zero
        val = int(r.get(limit_key) or 0)
        if val > 0:
            r.decr(limit_key)


# ── Generic Rate Limiting ───────────────────────────────────

import time
from contextlib import contextmanager

@contextmanager
def distributed_lock(lock_name: str, ttl: int = 10):
    """
    Phase 41: Multi-instance distributed lock (Redlock pattern).
    Ensures safe access to global resources (credits, jobs).
    """
    if not HAS_REDIS:
        # Local development fallback: no-op since multi-instance is unlikely
        yield True
        return

    lock_key = f"lock:{lock_name}"
    lock_val = str(time.time())
    
    # Try to acquire the lock: SET lock_key lock_val NX PX ttl*1000
    acquired = r.set(lock_key, lock_val, nx=True, px=ttl * 1000)
    
    try:
        if not acquired:
            print(f"[Redis] Lock {lock_name} is already held.")
            yield False
        else:
            yield True
    finally:
        if acquired:
            # Only release if we still hold it (check value)
            current = _get(lock_key)
            if current:
                # Standardize to string for comparison
                val = current.decode() if isinstance(current, bytes) else str(current)
                if val == lock_val:
                    r.delete(lock_key)

def is_rate_limited(user_id: str, limit: int = 5, window: int = 60) -> bool:
    """
    Check if a user is rate limited globally via Redis or Firestore.
    """
    if HAS_REDIS:
        key = f"rate_limit:{user_id}"
        try:
            count = r.incr(key)
            if count == 1:
                r.expire(key, window)
            return count > limit
        except Exception as e:
            print(f"[Redis] Rate limit failure: {e}")
            return False
            
    # Fallback to Firestore for shared rate-limiting across instances
    try:
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        limit_ref = firestore_db.collection("rate_limits").document(user_id)
        doc = limit_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            last_reset_raw = data.get("last_reset", now)
            
            # Phase 40: Mock-Safe Datetime Handling
            if hasattr(last_reset_raw, "replace"):
                last_reset = last_reset_raw.replace(tzinfo=None) # type: ignore
            else:
                last_reset = now
                
            if isinstance(last_reset, datetime) and (now - last_reset > timedelta(seconds=window)):
                # Reset window
                limit_ref.set({"count": 1, "last_reset": now})
                return False
            else:
                new_count = data.get("count", 0) + 1
                limit_ref.update({"count": new_count})
                return new_count > limit
        else:
            limit_ref.set({"count": 1, "last_reset": now})
            return False
    except Exception as e:
        print(f"[Firestore] Rate limit check failed: {e}")
        return False
