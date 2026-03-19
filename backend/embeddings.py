
import numpy as np

import threading

import logging

import hashlib



logger = logging.getLogger(__name__)



HAS_MODEL = False

model = None

_model_lock = threading.Lock()





def load_embedding_model():

    def _load():

        global model, HAS_MODEL

        try:

            from sentence_transformers import SentenceTransformer

            logger.info("Loading sentence-transformer model (background)...")

            _model = SentenceTransformer("paraphrase-MiniLM-L6-v2", device="cpu")

            with _model_lock:

                model = _model

                HAS_MODEL = True

            logger.info("Sentence-transformer loaded — semantic search active.")

        except Exception as e:

            logger.warning(f"Sentence-transformer unavailable: {e}. Using deterministic fallback.")

            with _model_lock:

                HAS_MODEL = False



    t = threading.Thread(target=_load, daemon=True)

    t.start()





load_embedding_model()





def embed_text(text: str) -> list:

    with _model_lock:

        m = model

        has = HAS_MODEL

    if has and m is not None:

        try:

            return m.encode(text).tolist()

        except Exception as e:

            logger.error(f"Embedding error: {e}")

    # Deterministic fallback — same text always gets same vector

    seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)

    rng = np.random.default_rng(seed)

    return rng.uniform(-1, 1, 384).tolist()





def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:

    na, nb = np.linalg.norm(a), np.linalg.norm(b)

    if na == 0 or nb == 0:

        return 0.0

    return float(np.dot(a, b) / (na * nb))

