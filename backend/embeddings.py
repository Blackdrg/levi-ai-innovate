
import numpy as np

import threading

import logging

import hashlib



import os
import random

logger = logging.getLogger(__name__)

# Environment check
RENDER = os.getenv("RENDER") == "true"

HAS_MODEL = False
model = None
_model_lock = threading.Lock()

def embed_text(text: str) -> list:
    """
    Returns a 384-dim vector for the given text.
    On Render Free Tier, we skip the heavy model to save RAM.
    """
    global model, HAS_MODEL

    # 1. Skip if on Render Free Tier
    if RENDER:
        # Deterministic hash-seeded random so the same text always gets the same vector
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        return rng.uniform(-1, 1, 384).tolist()

    # 2. Lazy load model if not on Render
    if model is None and not HAS_MODEL:
        with _model_lock:
            if model is None: # Double check pattern
                try:
                    from sentence_transformers import SentenceTransformer
                    logger.info("Lazy-loading sentence-transformer model...")
                    model = SentenceTransformer("paraphrase-MiniLM-L6-v2", device="cpu")
                    HAS_MODEL = True
                except Exception as e:
                    logger.warning(f"Failed to load model: {e}")
                    HAS_MODEL = False

    # 3. Use model if available
    if HAS_MODEL and model is not None:
        try:
            return model.encode(text).tolist()
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

