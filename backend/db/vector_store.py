# backend/db/vector_store.py
"""
LEVI-AI Vector Store Bridge (v7 Sovereign).
Unified entry point for semantic embeddings, FAISS storage, and secure vaulting.
"""
import os
import json
import logging
import hashlib
import threading
import numpy as np  # type: ignore
from typing import List, Dict, Any, Optional

# Re-exporting these for the core Brain engines
from backend.utils.vector_db import VectorDB
from backend.utils.encryption import SovereignVault

logger = logging.getLogger(__name__)

# Environment check
RENDER = os.getenv("RENDER") == "true"

HAS_MODEL = False
_model = None
_model_lock = threading.Lock()

def embed_text(text: str) -> list:
    """
    Returns a 384-dim vector for the given text.
    On Render Free Tier, we skip the heavy model to save RAM.
    """
    global _model, HAS_MODEL
    
    # 0. v10.0 Local Sovereignty Override
    OFFLINE = os.getenv("OFFLINE_MODE") == "true"

    # 1. Skip if on Render Free Tier OR in Offline Mode (if we want to use hash-fallback)
    # However, for Local Sovereignty, we PREFER the actual local model over hashes.
    if RENDER and not OFFLINE:
        # Deterministic hash-seeded random so the same text always gets the same vector
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        return rng.uniform(-1, 1, 384).tolist()

    # 2. Lazy load model if not on Render
    if _model is None and not HAS_MODEL:
        with _model_lock:
            if _model is None: # Double check pattern
                try:
                    from sentence_transformers import SentenceTransformer  # type: ignore
                    logger.info("Lazy-loading sentence-transformer model...")
                    _model = SentenceTransformer("paraphrase-MiniLM-L6-v2", device="cpu")
                    HAS_MODEL = True
                except Exception as e:
                    logger.warning(f"Failed to load model: {e}")
                    HAS_MODEL = False

    # 3. Use model if available
    if HAS_MODEL and _model is not None:
        try:
            return _model.encode(text).tolist()
        except Exception as e:
            logger.error(f"Embedding error: {e}")

    # 4. Deterministic fallback (same text = same vector)
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(seed)
    return rng.uniform(-1, 1, 384).tolist()

# Legacy Class for backward compatibility (Optional)
class VectorIndex:
    def __init__(self, *args, **kwargs):
        logger.warning("VectorIndex is legacy. Use VectorDB for v7 missions.")
        self.db = VectorDB("legacy")

class SovereignVectorStore:
    """
    LEVI-AI v13.0: High-Level Vector Store Bridge.
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

# Graduation Alias for the Absolute Monolith v13
VectorStoreV13 = SovereignVectorStore
