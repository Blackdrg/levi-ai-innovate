import numpy as np
import random
import threading
import logging

logger = logging.getLogger(__name__)

HAS_MODEL = False
model = None

def load_embedding_model():
    def _load():
        global model, HAS_MODEL
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Attempting to load sentence-transformer model in background...")
            model = SentenceTransformer('paraphrase-MiniLM-L6-v2', device='cpu')
            HAS_MODEL = True
            logger.info("Sentence-transformer model loaded successfully.")
        except Exception as e:
            logger.warning(f"Failed to load sentence-transformer model: {e}. Using mock embeddings.")
            HAS_MODEL = False

    thread = threading.Thread(target=_load)
    thread.daemon = True
    thread.start()

# Start loading in background
load_embedding_model()

def embed_text(text: str) -> list[float]:
    if HAS_MODEL and model is not None:
        try:
            emb = model.encode(text)
            return emb.tolist()
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return [random.uniform(-1, 1) for _ in range(384)]
    else:
        # Mock embedding (384 dimensions)
        return [random.uniform(-1, 1) for _ in range(384)]

def cosine_sim(a: np.ndarray, b: np.ndarray):
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0
    return np.dot(a, b) / (norm_a * norm_b)

