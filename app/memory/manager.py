import asyncpg, redis.asyncio as redis, numpy as np
from app.memory.hnsw_store import HNSWStore
from app.memory.neo4j_store import Neo4jStore
from app.db.postgres import get_db_pool
import os, json, asyncio

class MemoryManager:
    """
    Sovereign v13: Unified 5-Tier Memory Controller.
    Interfaces with Redis (T1), Postgres (T2), HNSW (T3), and Neo4j (T5).
    """
    def __init__(self):
        self.hnsw = HNSWStore(os.getenv("VECTOR_DB_PATH", "./vault/vector_hnsw.index"))
        self.graph = Neo4jStore()
        self._redis = None
        self._pg = None

    async def _get_redis(self):
        if not self._redis:
            self._redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        return self._redis

    async def search(self, query: str, user_id: str, top_k: int = 5) -> list:
        # T1: Session Cache (Redis)
        r = await self._get_redis()
        cache_key = f"search:{user_id}:{hash(query)}"
        cached = await r.get(cache_key)
        if cached:
            return json.loads(cached)

        # T3: Semantic Resonance (HNSW)
        # Using a default vector for stub search
        dummy_vec = [0.1] * 384
        results = self.hnsw.search(dummy_vec, top_k=top_k, user_id=user_id)

        # T4: Crystallized Hive Wisdom (Optional check)
        # In a real implementation, this searches the local training/quote archive.

        # Cache results for 5 minutes
        await r.setex(cache_key, 300, json.dumps(results))
        return results

    async def store(self, text: str, user_id: str, importance: float, mission_id: str):
        """
        Sovereign v13: Unified 5-Tier Persistence.
        """
        # T2: Episodic Record (Postgres)
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_facts (user_id, fact, importance, mission_id)
                VALUES ($1, $2, $3, $4)
            """, user_id, text, importance, mission_id)

        # T4: Crystallized Sample (JSONL)
        if importance >= 0.9:
            asyncio.create_task(self._crystallize_sample(text, user_id))

        # T5: Graph Resonance (Neo4j)
        asyncio.create_task(
            self.graph.store_knowledge(f"user:{user_id}", "realized", text[:50])
        )

    async def _crystallize_sample(self, text: str, user_id: str):
        """Tier 4: Writes high-fidelity samples to local training log."""
        log_path = "/app/vault/crystallized_wisdom.jsonl"
        entry = {"user_id": user_id, "text": text, "timestamp": datetime.now().isoformat()}
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
