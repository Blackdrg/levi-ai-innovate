"""
Sovereign Redis v8.
Central Redis client for caching, rate limiting, and session persistence.
"""

import os
import json
import logging
import redis 
import redis.asyncio as async_redis
from typing import Any, Optional, List, Dict
from backend.utils.network import redis_breaker

logger = logging.getLogger(__name__)

# --- Redis Configuration ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
HAS_REDIS = False
r = None
r_async = None
HAS_REDIS_ASYNC = False

# Synchronous Heartbeat (Safe for module load)
try:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    HAS_REDIS = True
    logger.info("Sovereign Redis: Sync heartbeat detected.")
except Exception as e:
    logger.error(f"Sovereign Redis Sync: Pulse not found: {e}")

# Asynchronous Client (Requires explicit await/event loop)
try:
    r_async = async_redis.from_url(REDIS_URL, decode_responses=True)
    HAS_REDIS_ASYNC = True
except Exception as e:
    logger.error(f"Sovereign Redis Async: Failed to initialize: {e}")

# --- Central Interface ---
def get_redis_client() -> Optional[redis.Redis]:
    return r if HAS_REDIS else None

def is_jti_blacklisted(jti: str) -> bool:
    if not HAS_REDIS or not jti: return False
    return redis_breaker.call(r.exists, f"blacklist:{jti}") > 0

# --- Conversation/Memory Helpers ---
def save_conversation_buffered(session_id: str, history: List[Dict[str, Any]], user_id: str = "guest"):
    """Saves session history to Redis with a rolling window."""
    if not HAS_REDIS or not session_id: return
    try:
        key = f"chat:{user_id}:{session_id}"
        redis_breaker.call(r.setex, key, 86400 * 7, json.dumps(history)) # 7 day TTL
    except Exception as e:
        logger.error(f"Redis save anomaly: {e}")

def get_conversation(session_id: str, user_id: str = "guest") -> List[Dict[str, Any]]:
    if not HAS_REDIS: return []
    try:
        key = f"chat:{user_id}:{session_id}"
        data = redis_breaker.call(r.get, key)
        return json.loads(data) if data else []
    except Exception:
        return []

# --- JSON Caching Helpers ---
def cache_json(key: str, data: Any, ttl: int = 600):
    if not HAS_REDIS: return
    try:
        redis_breaker.call(r.setex, key, ttl, json.dumps(data))
    except Exception: pass

def get_cached_json(key: str) -> Optional[Any]:
    if not HAS_REDIS: return None
    try:
        data = redis_breaker.call(r.get, key)
        return json.loads(data) if data else None
    except Exception: return None
# --- Matching & Caching Layers ---
def check_exact_match(user_id: str, message: str, mood: str) -> Optional[str]:
    import hashlib
    raw = f"{user_id}:{mood}:{message.strip().lower()}"
    key = f"exact_match:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"
    if not HAS_REDIS: return None
    try:
        raw_res = redis_breaker.call(r.get, key)
        return raw_res.decode('utf-8') if isinstance(raw_res, bytes) else raw_res
    except Exception: return None

def store_exact_match(user_id: str, message: str, mood: str, response: str, ttl: int = 3600):
    import hashlib
    raw = f"{user_id}:{mood}:{message.strip().lower()}"
    key = f"exact_match:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"
    if HAS_REDIS:
        try: redis_breaker.call(r.setex, key, ttl, response)
        except Exception: pass

def check_semantic_match(user_id: str, message: str, mood: str, threshold: float = 0.95) -> Optional[str]:
    if not HAS_REDIS: return None
    from backend.db.vector import VectorStore # Use new vector tier
    # Logic bridged to VectorStore for v8 semantic caching
    return None

# --- Budgeting & Spend Tracking ---
from datetime import date as _date

def incr_daily_ai_spend(user_id: str = "global", amount: float = 1.0) -> float:
    key = f"ai_spend:{user_id}:{_date.today().isoformat()}"
    if HAS_REDIS:
        try:
            pipe = r.pipeline()
            pipe.incrbyfloat(key, amount)
            pipe.expire(key, 172800) # 2 days
            result = pipe.execute()
            return float(result[0])
        except Exception: return 0.0
    return 0.0

def get_daily_ai_spend(user_id: str = "global") -> float:
    key = f"ai_spend:{user_id}:{_date.today().isoformat()}"
    if not HAS_REDIS: return 0.0
    try:
        raw = redis_breaker.call(r.get, key)
        return float(raw) if raw else 0.0
    except Exception: return 0.0

def get_user_credits(user_id: str) -> int:
    key = f"user_credits:{user_id}"
    if not HAS_REDIS: return 0
    try:
        cached = redis_breaker.call(r.get, key)
        if cached: return int(cached)
        # Bridge to Firebase for sync
        from .firebase import db as firestore_db
        user_doc = firestore_db.collection("users").document(user_id).get(timeout=5)
        if user_doc.exists:
            credits = int(user_doc.to_dict().get("credits", 0))
            redis_breaker.call(r.setex, key, 300, credits)
            return credits
    except Exception: pass
    return 0

# --- Concurrency & Locking ---
from contextlib import contextmanager
import time

@contextmanager
def distributed_lock(lock_name: str, ttl: int = 10):
    if not HAS_REDIS:
        yield True
        return
    lock_key = f"lock:{lock_name}"
    lock_val = str(time.time() + ttl)
    acquired = redis_breaker.call(r.set, lock_key, lock_val, nx=True, px=ttl * 1000)
    try: yield bool(acquired)
    finally:
        if acquired: r.delete(lock_key)

def incr_failure_count(agent_name: str):
    if HAS_REDIS:
        key = f"stats:failures:{agent_name}"
        try:
            redis_breaker.call(r.incr, key)
            redis_breaker.call(r.expire, key, 604800)
        except Exception: pass

def get_failure_count(agent_name: str) -> int:
    if HAS_REDIS:
        try:
            val = redis_breaker.call(r.get, f"stats:failures:{agent_name}")
            return int(val) if val else 0
        except Exception: return 0
    return 0

# --- Working Memory (Mini-System Helpers) ---
def store_working_context(user_id: str, user_input: str, output: str):
    """Simple list-based working context for rapid mini-system retrieval."""
    if not HAS_REDIS: return
    try:
        key = f"working_ctx:{user_id}"
        redis_breaker.call(r.lpush, key, f"{user_input} -> {output}")
        redis_breaker.call(r.ltrim, key, 0, 10) # Keep last 10 entries
        redis_breaker.call(r.expire, key, 3600) # 1 hour TTL
    except Exception: pass

def get_working_context(user_id: str, limit: int = 5) -> List[str]:
    """Retrieves the recent working context buffer."""
    if not HAS_REDIS: return []
    try:
        return redis_breaker.call(r.lrange, f"working_ctx:{user_id}", 0, limit - 1)
    except Exception: return []
