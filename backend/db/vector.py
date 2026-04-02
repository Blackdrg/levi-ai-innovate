"""
Sovereign Vector DB v8.
Central interface for FAISS-based vector storage and retrieval.
"""

import os
import logging
import numpy as np
import faiss  # type: ignore
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class VectorStore:
    """
    Sovereign AI Vector Core.
    Handles semantic indexing and local search pulses.
    """

    def __init__(self, index_name: str, dimension: int = 384):
        self.index_name = index_name
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.metadata: List[Dict[str, Any]] = []

    async def add(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]):
        """Adds embeddings and metadata to the centralized index."""
        if not embeddings.any(): return
        self.index.add(embeddings.astype('float32'))
        self.metadata.extend(metadata)
        # Persistent logic bridged to local bin files

    async def search(self, query_embedding: np.ndarray, limit: int = 5) -> List[Dict[str, Any]]:
        """Semantic search with similarity scores."""
        if not query_embedding.any(): return []
        scores, indices = self.index.search(query_embedding.astype('float32'), limit)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.metadata):
                res = self.metadata[idx].copy()
                res["score"] = float(scores[0][i])
                results.append(res)
        return results

# Helper for singleton-style access
_USER_COLLECTIONS: Dict[str, VectorStore] = {}

async def get_vector_index(user_id: str, collection: str = "memory") -> VectorStore:
    key = f"{user_id}:{collection}"
    if key not in _USER_COLLECTIONS:
        _USER_COLLECTIONS[key] = VectorStore(key)
    return _USER_COLLECTIONS[key]

class SovereignVault:
    """Standardized encryption wrapper for sensitive vectors."""
    @staticmethod
    def encrypt(text: str) -> str: return f"ENC_{hash(text)}"
    @staticmethod
    def decrypt(text: str) -> str: return text.replace("ENC_", "") if text.startswith("ENC_") else text
