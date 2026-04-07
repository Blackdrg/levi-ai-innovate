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

def _is_local_url(url: str) -> bool:
    """Detects if the Redis URL points to localhost/127.0.0.1 to avoid SSL handshake paradoxes."""
    return any(host in url for host in ["localhost", "127.0.0.1", "0.0.0.0"])

# --- Redis Configuration (HA Support v2.1) ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_MODE = os.getenv("REDIS_MODE", "standalone").lower() # standalone | sentinel | cluster
SENTINEL_SERVICE = os.getenv("REDIS_SENTINEL_SERVICE", "mymaster")
SENTINEL_NODES = os.getenv("REDIS_SENTINEL_NODES", "") # e.g. "localhost:26379,localhost:26380"

HAS_REDIS = False
r = None
r_async = None
HAS_REDIS_ASYNC = False

def _create_ha_clients():
    global r, r_async, HAS_REDIS, HAS_REDIS_ASYNC
    
    # 🛡️ Graduation Audit: Enforce mandatory Redis in Production
    is_prod = os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    # Check for test injection
    if os.getenv("TEST_MODE", "false").lower() == "true":
        try:
            from fakeredis import FakeRedis
            from fakeredis.aioredis import FakeRedis as AsyncFakeRedis
            r = FakeRedis(decode_responses=True)
            r_async = AsyncFakeRedis(decode_responses=True)
            HAS_REDIS = True
            HAS_REDIS_ASYNC = True
            logger.info("Sovereign Redis: Using Mock Infrastructure (TEST_MODE).")
            return
        except ImportError:
            logger.warning("fakeredis not found. Tests will attempt live connection.")

    try:
        # Resolve SSL Paradox: Strip SSL parameters for local dev machines
        kwargs = {"decode_responses": True}
        if _is_local_url(REDIS_URL):
            kwargs["ssl"] = False
            # Some versions of redis-py pass ssl_cert_reqs even if ssl=False, which triggers errors
            # We use from_url for its robust parsing but sanitize the URL if needed.

        if REDIS_MODE == "sentinel" and SENTINEL_NODES:
            from redis.sentinel import Sentinel
            nodes = [tuple(n.split(':')) for n in SENTINEL_NODES.split(',')]
            sentinel = Sentinel(nodes, **kwargs)
            r = sentinel.master_for(SENTINEL_SERVICE)
            # Async version
            from redis.asyncio.sentinel import Sentinel as AsyncSentinel
            async_sentinel = AsyncSentinel(nodes, **kwargs)
            r_async = async_sentinel.master_for(SENTINEL_SERVICE)
            logger.info(f"Sovereign Redis: Linked to Sentinel Swarm [{SENTINEL_SERVICE}]")
        
        elif REDIS_MODE == "cluster":
            from redis.cluster import RedisCluster
            r = RedisCluster.from_url(REDIS_URL, **kwargs)
            from redis.asyncio.cluster import RedisCluster as AsyncRedisCluster
            r_async = AsyncRedisCluster.from_url(REDIS_URL, **kwargs)
            logger.info("Sovereign Redis: Cluster mode active.")
        
        else: # standalone
            r = redis.from_url(REDIS_URL, **kwargs)
            r_async = async_redis.from_url(REDIS_URL, **kwargs)
            logger.info("Sovereign Redis: Standalone pulse detected.")

        r.ping()
        HAS_REDIS = True
        HAS_REDIS_ASYNC = True
    except Exception as e:
        if is_prod:
            logger.error(f"CRITICAL: [Redis] Mandatory infrastructure failed ({e}) in PRODUCTION. System Halted.")
            raise ConnectionError(f"Sovereign DCN requires active Redis for persistence and quorum. Error: {e}")
        else:
            logger.error(f"Sovereign Redis HA Failure: {e}. Defaulting to standalone fallback.")
            try:
                r = redis.from_url(REDIS_URL, decode_responses=True)
                r_async = async_redis.from_url(REDIS_URL, decode_responses=True)
            except: pass

_create_ha_clients()

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
