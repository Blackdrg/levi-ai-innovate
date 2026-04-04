# embeddings.py
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
import asyncio
from typing import List, Union

logger = logging.getLogger(__name__)

# nomic-ai/nomic-embed-text-v1.5: Best local performance/relevance balance
MODEL_PATH = "nomic-ai/nomic-embed-text-v1.5"

class LocalEmbedder:
    _instance = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    logger.info(f"[Embedder] Loading local sentence-transformers model: {MODEL_PATH}")
                    # Offload model loading to a thread to prevent blocking
                    cls._instance = await asyncio.to_thread(
                        lambda: SentenceTransformer(MODEL_PATH, trust_remote_code=True)
                    )
        return cls._instance

async def embed(text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
    """Generates normalized semantic vectors for input text or list of texts."""
    model = await LocalEmbedder.get_instance()
    
    # Offload encoding to a thread
    embeddings = await asyncio.to_thread(
        lambda: model.encode(text, normalize_embeddings=True)
    )
    
    return embeddings.tolist()
