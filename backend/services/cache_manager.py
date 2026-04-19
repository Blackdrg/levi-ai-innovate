"""
LEVI-AI Multi-Level Cache Manager v14.1.
T0: Rule Graduation (Deterministic O(1) - Memory-Mapped)
T1: Response Cache (Exact Match - Redis)
T2: Semantic Cache (Vector Similarity - FAISS/VectorDB)
T3: Strategy Cache (DAG Template Reuse - Redis)
"""

import logging
import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from backend.db.redis import state_bridge, HAS_REDIS
from backend.embeddings import embed_text
from backend.memory.vector_store import SovereignVectorStore
from backend.core.orchestrator_types import BrainMode, EngineRoute

logger = logging.getLogger(__name__)

class CacheManager:
    DEFAULT_TTL = 86400 # 24 hours
    SEMANTIC_THRESHOLD = 0.92
    
    # 🎓 Tier-0: Deterministic O(1) Graduated Rules
    _T0_BYPASS_CACHE: Dict[str, Any] = {
        "analysis:security": {"mode": BrainMode.DEEP, "temperature": 0.2, "fidelity_enforced": True},
        "planning:rapid": {"mode": BrainMode.FAST, "temperature": 0.9, "fidelity_enforced": False},
        "mission:audit": {"mode": BrainMode.SECURE, "temperature": 0.0, "fidelity_enforced": True},
        "system:diagnostics": {"mode": BrainMode.BALANCED, "temperature": 0.5, "fidelity_enforced": True}
    }

    @classmethod
    async def get_rule_bypass(cls, intent_type: str) -> Optional[Dict[str, Any]]:
        """T0: Graduated Rule Promotion Bypass (Sub-millisecond)."""
        rule = cls._T0_BYPASS_CACHE.get(intent_type)
        if rule:
            logger.info(f"🎓 [Cache] T0 GRADUATION HIT: Bypassing inference for {intent_type}")
            return rule
        return None

    @classmethod
    def _get_key(cls, category: str, text: str) -> str:
        h = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"cache:{category}:{h}"

    @classmethod
    async def get_response(cls, user_input: str) -> Optional[Dict[str, Any]]:
        """T1: Exact Match Response Cache."""
        if not HAS_REDIS: return None
        
        key = cls._get_key("resp", user_input)
        cached = await state_bridge.get(key)
        if cached:
            logger.info(f"[Cache] T1 HIT for query: {user_input[:40]}...")
            return json.loads(cached)
        return None

    @classmethod
    async def get_semantic_response(cls, user_input: str) -> Optional[Dict[str, Any]]:
        """T2: Semantic Similarity Cache."""
        # We reuse the SovereignVectorStore but with a specific 'cache' category
        try:
            results = await SovereignVectorStore.search_facts("system_cache", user_input, limit=1)
            if results and results[0]["score"] > cls.SEMANTIC_THRESHOLD:
                logger.info(f"[Cache] T2 HIT (score={results[0]['score']:.4f})")
                return json.loads(results[0]["fact"])
        except Exception as e:
            logger.error(f"[Cache] T2 lookup failure: {e}")
        return None

    @classmethod
    async def set_response(cls, user_input: str, response_payload: Dict[str, Any], semantic: bool = True):
        """Stores response in T1 and optionally T2."""
        if not HAS_REDIS: return
        
        payload_json = json.dumps(response_payload)
        
        # T1: Resilient Cache
        key = cls._get_key("resp", user_input)
        await state_bridge.set(key, payload_json, ex=cls.DEFAULT_TTL)
        
        # T2: Semantic
        if semantic:
            from backend.utils.runtime_tasks import create_tracked_task
            create_tracked_task(
                SovereignVectorStore.store_fact(
                    "system_cache",
                    payload_json,
                    category="response_cache",
                    importance=1.0
                ),
                name="cache-t2-store"
            )

    @classmethod
    async def get_strategy(cls, intent_type: str, signature: str) -> Optional[Dict[str, Any]]:
        """T3: Strategy Cache (DAG Reuse)."""
        if not HAS_REDIS: return None
        key = f"cache:strat:{intent_type}:{signature}"
        cached = await state_bridge.get(key)
        if cached:
            return json.loads(cached)
        return None

    @classmethod
    async def set_strategy(cls, intent_type: str, signature: str, graph_data: Dict[str, Any]):
        if not HAS_REDIS: return
        key = f"cache:strat:{intent_type}:{signature}"
        await state_bridge.set(key, json.dumps(graph_data), ex=cls.DEFAULT_TTL * 7) # Strategies last longer (1 week)
