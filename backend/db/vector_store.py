# backend/db/vector_store.py
"""
LEVI-AI Vector Store Bridge (v7 Sovereign).
Unified entry point for semantic embeddings, FAISS storage, and secure vaulting.
"""
import os
import logging
import hashlib
import numpy as np  # type: ignore
from typing import List, Dict, Any

# Re-exporting these for the core Brain engines
from backend.utils.vector_db import VectorDB
from backend.utils.encryption import SovereignVault

from backend.utils.circuit_breaker import ollama_breaker
logger = logging.getLogger(__name__)

async def embed_text(text: str) -> list:
    """
    Returns a 768-dim vector for the given text using local Ollama.
    """
    import httpx
    
    # Sovereign v14.0.0: High-fidelity Local Embeddings
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL_EMBED", "nomic-embed-text")
    
    async def _do_embed():
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/api/embeddings",
                json={
                    "model": model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            return response.json()["embedding"]

    try:
        return await ollama_breaker.call(_do_embed)
    except Exception as e:
        logger.error(f"[VectorStore] Ollama Embedding Error: {e}")
        
        # 4. Deterministic fallback (same text = same vector) if local engine is down
        # Warning: Fallback uses 768-dim to match nomic-embed-text
        dim = 768
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        return rng.uniform(-1, 1, dim).tolist()

# Legacy Class for backward compatibility (Optional)
class VectorIndex:
    def __init__(self, *args, **kwargs):
        logger.warning("VectorIndex is legacy. Use VectorDB for v7 missions.")
        self.db = VectorDB("legacy")

class SovereignVectorStore:
    """
    LEVI-AI v14.0.0: High-Level Vector Store Bridge.
    Unified interface for the Learning System and Evolutionary Engines.
    Provides sub-30ms HNSW retrieval via VectorDB.
    """
    def __init__(self, collection: str = "global"):
        self.collection_name = collection

    async def search_global(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Wraps global collection search for the Learning engine."""
        db = await VectorDB.get_collection(self.collection_name)
        return await db.search(query, limit=limit)

    async def add(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        """Wraps global collection addition."""
        db = await VectorDB.get_collection(self.collection_name)
        await db.add(texts, metadatas)

    @staticmethod
    async def clear_user_memory(user_id: str):
        """Standard v8 absolute memory wipe bridge."""
        db = await VectorDB.get_user_collection(user_id, "memory")
        await db.clear()

# Graduation Alias for the Sovereign OS v14.0.0
VectorStoreV14 = SovereignVectorStore


class VectorStoreV13(SovereignVectorStore):
    """
    Legacy compatibility adapter for older dreaming/distillation flows.
    """

    async def search(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        db = await VectorDB.get_user_collection(user_id, "memory")
        return await db.search(query, limit=limit)
