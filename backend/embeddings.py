import numpy as np
import random

try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('paraphrase-MiniLM-L6-v2', device='cpu')
    HAS_MODEL = True
except Exception as e:
    print(f"Warning: Failed to load sentence-transformer model: {e}")
    HAS_MODEL = False


def embed_text(text: str) -> list[float]:
    if HAS_MODEL:
        emb = model.encode(text)
        return emb.tolist()
    else:
        # Mock embedding (384 dimensions)
        return [random.uniform(-1, 1) for _ in range(384)]

def cosine_sim(a: np.ndarray, b: np.ndarray):
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0
    return np.dot(a, b) / (norm_a * norm_b)

