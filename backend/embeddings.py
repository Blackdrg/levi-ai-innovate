import numpy as np
import hashlib
import threading
import logging

logger = logging.getLogger(__name__)

# Flags and locks
HAS_MODEL = False
model = None
_model_lock = threading.Lock()

def _load_in_background():
    """Background thread to load the model without blocking startup."""
    global model, HAS_MODEL
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformer model (background)...")
        # Use CPU explicitly for free-tier compatibility
        _model = SentenceTransformer("paraphrase-MiniLM-L6-v2", device="cpu")
        with _model_lock:
            model = _model
            HAS_MODEL = True
        logger.info("Sentence-transformer loaded — semantic search active.")
    except Exception as e:
        logger.warning(f"Sentence-transformer unavailable: {e}. Using deterministic hash-fallback.")
        with _model_lock:
            HAS_MODEL = False

# Kick off loading immediately on import
threading.Thread(target=_load_in_background, daemon=True).start()

def embed_text(text: str) -> list:
    """
    Returns a 384-dim vector for the given text.
    If model is not loaded, uses a deterministic hash-seeded fallback.
    """
    with _model_lock:
        m = model
        has = HAS_MODEL

    if has and m is not None:
        try:
            return m.encode(text).tolist()
        except Exception as e:
            logger.error(f"Embedding error: {e}")

    # Deterministic fallback: hash-seeded random so the same text always
    # gets the same vector — better than pure random for repeated queries
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(seed)
    return rng.uniform(-1, 1, 384).tolist()

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))
