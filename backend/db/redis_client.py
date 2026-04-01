# pyright: reportMissingImports=false

import redis  # type: ignore
import os
import json
import redis
import redis.asyncio as aioredis
from typing import Optional, Any, Dict
from dotenv import load_dotenv  # type: ignore

load_dotenv()

from backend.db.firestore_db import db as firestore_db # type: ignore

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
        print(f"CRITICAL: {error_msg} Starting in DEGRADED mode. Features requiring shared state across instances will be limited.")
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
    return json.loads(cast(Any, raw))

def get_conversation(session_id: str) -> list:
    raw = _get(f"conv:{session_id}")
    if raw:
        return json.loads(cast(Any, raw))
    
    try:
        doc = firestore_db.collection("conversations").document(session_id).get()
        if doc.exists:
            conv = doc.to_dict().get("history", [])
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
    """Legacy/Direct save (use save_conversation_buffered for production)."""
    _set(f"conv:{session_id}", json.dumps(conversation), ex=3600)
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

def save_conversation_buffered(session_id: str, conversation: list, user_id: str = None):
    _set(f"conv:{session_id}", json.dumps(conversation), ex=3600)
    
    if HAS_REDIS:
        try:
            from datetime import datetime
            payload = {
                "session_id": session_id,
                "user_id": user_id,
                "history": conversation,
                "updated_at": datetime.utcnow().isoformat()
            }
            r.rpush("conv_buffer", json.dumps(payload))
            r.expire("conv_buffer", 3600)
        except Exception as e:
            print(f"[Redis] Error buffering conversation {session_id}: {e}")
            save_conversation(session_id, conversation, user_id)
    else:
        save_conversation(session_id, conversation, user_id)

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
    if HAS_REDIS:
        _set(f"jti:{jti}", "1", ex=expires_in)
    else:
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
    if HAS_REDIS:
        return _get(f"jti:{jti}") is not None

    try:
        doc = firestore_db.collection("blacklisted_jtis").document(jti).get()
        if not doc.exists:
            return False
        
        data = doc.to_dict()
        expires_at = data.get("expires_at")
        
        if expires_at is None:
            return True
            
        from datetime import datetime
        now = datetime.utcnow()
        
        if hasattr(expires_at, "replace"):
            exp_naive = expires_at.replace(tzinfo=None) # type: ignore
        else:
            exp_naive = now
            
        return exp_naive > now
    except Exception as e:
        print(f"[Firestore] Blacklist check error: {e}")
        return False

def delete_jti(jti: str):
    if HAS_REDIS:
        r.delete(f"jti:{jti}")
    else:
        try:
            firestore_db.collection("blacklisted_jtis").document(jti).delete()
        except Exception:
            pass

def cache_user_memory(user_id: int, memory_dict: dict):
    _set(f"usermem:{user_id}", json.dumps(memory_dict), ex=600)

def get_cached_user_memory(user_id: int) -> dict | None:
    raw = _get(f"usermem:{user_id}")
    if not raw:
        return None
    return json.loads(cast(Any, raw))

def invalidate_user_memory(user_id: int):
    if HAS_REDIS:
        r.delete(f"usermem:{user_id}")
    else:
        _memory_cache.pop(f"usermem:{user_id}", None)

from datetime import date as _date

def incr_daily_ai_spend(user_id: str = "global", amount: float = 1.0) -> float:
    key = f"ai_spend:{user_id}:{_date.today().isoformat()}"
    if HAS_REDIS:
        pipe = r.pipeline()
        pipe.incrbyfloat(key, amount)
        pipe.expire(key, 86400 * 2)
        result = pipe.execute()
        return float(result[0])
    else:
        current = float(_memory_cache.get(key) or 0)
        current += amount
        _memory_cache[key] = str(current)
        return current

def get_daily_ai_spend(user_id: str = "global") -> float:
    key = f"ai_spend:{user_id}:{_date.today().isoformat()}"
    raw = _get(key)
    if raw is None:
        return 0.0
    return float(raw)

def get_user_credits(user_id: str) -> int:
    key = f"user_credits:{user_id}"
    cached = _get(key)
    if cached:
        return int(cached)
    
    try:
        user_doc = firestore_db.collection("users").document(user_id).get(timeout=5)
        if user_doc.exists:
            credits = int(user_doc.to_dict().get("credits", 0))
            if HAS_REDIS:
                r.setex(key, 300, credits)
            return credits
    except Exception as e:
        print(f"[Redis/Firestore] Credit retrieval failed: {e}")
    return 0

def cache_json(key: str, data: Any, ttl: int = 3600):
    try:
        if is_serializable(data):
            _set(key, json.dumps(data), ex=ttl)
    except Exception as e:
        print(f"[Redis] cache_json failed for {key}: {e}")

def get_cached_json(key: str) -> Optional[Any]:
    try:
        raw = _get(key)
        if raw:
            return json.loads(cast(Any, raw))
    except Exception as e:
        print(f"[Redis] get_cached_json failed for {key}: {e}")
    return None

def check_exact_match(user_id: str, message: str, mood: str) -> Optional[str]:
    import hashlib
    raw = f"{user_id}:{mood}:{message.strip().lower()}"
    key = f"exact_match:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"
    raw_res = _get(key)
    return raw_res.decode('utf-8') if isinstance(raw_res, bytes) else raw_res

def store_exact_match(user_id: str, message: str, mood: str, response: str, ttl: int = 3600):
    import hashlib
    raw = f"{user_id}:{mood}:{message.strip().lower()}"
    key = f"exact_match:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"
    _set(key, response, ex=ttl)

def check_semantic_match(user_id: str, message: str, mood: str, threshold: float = 0.92) -> Optional[str]:
    if not HAS_REDIS: return None
    
    from backend.db.vector_store import embed_text, cosine_sim
    import numpy as np
    
    current_emb = np.array(embed_text(message))
    buffer_key = f"semantic_buffer:{user_id}:{mood}"
    raw_buffer = r.lrange(buffer_key, 0, 49)
    
    for item in raw_buffer:
        try:
            data = json.loads(item)
            past_emb = np.array(data["embedding"])
            similarity = cosine_sim(current_emb, past_emb)
            
            if similarity >= threshold:
                return data["response"]
        except Exception: continue
        
    return None

def store_semantic_match(user_id: str, message: str, mood: str, response: str):
    if not HAS_REDIS: return
    
    from backend.db.vector_store import embed_text
    embedding = embed_text(message)
    
    buffer_key = f"semantic_buffer:{user_id}:{mood}"
    payload = json.dumps({
        "embedding": embedding,
        "response": response,
        "msg": message[:50]
    })
    
    r.lpush(buffer_key, payload)
    r.ltrim(buffer_key, 0, 99)
    r.expire(buffer_key, 86400)

def invalidate_cache(key: str):
    if HAS_REDIS:
        r.delete(key)
    else:
        _memory_cache.pop(key, None)

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
    if not HAS_REDIS:
        return True
    
    try:
        result = r.eval(ACQUIRE_SLOT_LUA, 1, limit_key, ttl, max_concurrent)
        return bool(result)
    except Exception as e:
        print(f"[Redis] Concurrency acquire failed: {e}")
        return True

def release_concurrency_slot(limit_key: str):
    if HAS_REDIS:
        val = int(r.get(limit_key) or 0)
        if val > 0:
            r.decr(limit_key)

import time
from contextlib import contextmanager

LUA_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

@contextmanager
def distributed_lock(lock_name: str, ttl: int = 10, retries: int = 0, backoff: float = 0.1):
    if not HAS_REDIS:
        yield True
        return

    lock_key = f"lock:{lock_name}"
    lock_val = str(time.time() + ttl)
    
    acquired = False
    for i in range(retries + 1):
        acquired = r.set(lock_key, lock_val, nx=True, px=ttl * 1000)
        if acquired:
            break
        if i < retries:
            import random
            time.sleep(backoff * (2 ** i) + random.uniform(0, 0.05))

    try:
        yield bool(acquired)
    finally:
        if acquired:
            try:
                r.eval(LUA_RELEASE_SCRIPT, 1, lock_key, lock_val)
            except Exception as e:
                print(f"[Redis] Atomic lock release failed for {lock_name}: {e}")

def is_rate_limited(user_id: str, limit: int = 5, window: int = 60) -> bool:
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
            
    try:
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        limit_ref = firestore_db.collection("rate_limits").document(user_id)
        doc = limit_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            last_reset_raw = data.get("last_reset", now)
            
            if hasattr(last_reset_raw, "replace"):
                last_reset = last_reset_raw.replace(tzinfo=None) # type: ignore
            else:
                last_reset = now
                
            if isinstance(last_reset, datetime) and (now - last_reset > timedelta(seconds=window)):
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

def incr_failure_count(agent_name: str):
    if HAS_REDIS:
        key = f"stats:failures:{agent_name}"
        r.incr(key)
        r.expire(key, 604800)

def get_failure_count(agent_name: str) -> int:
    if HAS_REDIS:
        key = f"stats:failures:{agent_name}"
        val = r.get(key)
        return int(val) if val else 0
    return 0
