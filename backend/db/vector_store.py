# backend/db/vector_store.py
import os
import json
import logging
import hashlib
import threading
import numpy as np  # type: ignore

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

    # 1. Skip if on Render Free Tier
    if RENDER:
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

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))

# Phase 12 FAISS integration (Placeholder for future expansion)
class VectorIndex:
    """Manages local vector search using FAISS (if available) or numpy."""
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = None
        self._init_index()

    def _init_index(self):
        try:
            import faiss # type: ignore
            self.index = faiss.IndexFlatL2(self.dimension)
            logger.info("FAISS index initialized.")
        except ImportError:
            logger.info("FAISS not found. Falling back to linear numpy search.")
            self.index = None
