"""
Sovereign Neural Embedding Engine v7.
Hardened for local sentence-transformers execution and cross-engine vector consistency.
"""

import os
import logging
import asyncio
from typing import List, Optional, Union
try:
    from sentence_transformers import SentenceTransformer # type: ignore
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None 
    HAS_SENTENCE_TRANSFORMERS = False

logger = logging.getLogger(__name__)

# --- Configuration ---
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")

class SovereignEmbedder:
    """
    Sovereign Neural Embedder Singleton.
    Provides semantic vector generation for memory, documents, and search.
    Hardened for multi-threaded local execution.
    """
    _instance: Optional[SentenceTransformer] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> Optional[SentenceTransformer]:
        """Retrieves and initializes the Embedding model singleton."""
        if cls._instance is not None:
            return cls._instance

        async with cls._lock:
            if cls._instance is not None:
                return cls._instance

            if not HAS_SENTENCE_TRANSFORMERS:
                logger.warning("[Embedder] Sentence-Transformers not installed. Neural embedding unavailable.")
                return None

            try:
                logger.info(f"[Embedder] Loading Neural Model: {MODEL_NAME} on {DEVICE}")
                # We use a thread to prevent blocking the event loop
                cls._instance = await asyncio.to_thread(
                    lambda: SentenceTransformer(MODEL_NAME, device=DEVICE)
                )
                return cls._instance
            except Exception as e:
                logger.error(f"[Embedder] Critical neural model load failure: {e}")
                return None

    @classmethod
    async def embed_text(cls, text: Union[str, List[str]]) -> List[List[float]]:
        """Generates semantic vectors for the provided text."""
        model = await cls.get_instance()
        if not model:
            # Fallback to zero-vector if neural model is missing
            length = 384 # MiniLM default
            return [[0.0] * length for _ in (text if isinstance(text, list) else [text])]
        
        try:
            # PII masking before embedding for privacy
            from backend.engines.utils.security import SovereignSecurity
            safe_text = [SovereignSecurity.mask_pii(t) for t in (text if isinstance(text, list) else [text])]
            
            # Weighted normalization for cross-engine consistency
            embeddings = await asyncio.to_thread(
                lambda: model.encode(safe_text, convert_to_numpy=True, normalize_embeddings=True)
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"[Embedder] Neural embedding failure: {e}")
            return []

# Global Accessor
embed_text = SovereignEmbedder.embed_text
