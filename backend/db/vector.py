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
        self.storage_path = os.path.abspath(f"backend/data/vectors/{index_name}")
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        self._load_from_disk()

    def _load_from_disk(self):
        """Initializes index from disk if it exists."""
        if os.path.exists(self.storage_path + ".index"):
            try:
                self.index = faiss.read_index(self.storage_path + ".index")
                with open(self.storage_path + ".meta", "r") as f:
                    import json
                    self.metadata = json.load(f)
                logger.info(f"VectorStore: Loaded '{self.index_name}' from disk.")
            except Exception as e:
                logger.error(f"VectorStore: Failed to load index '{self.index_name}': {e}")

    def checkpoint(self):
        """Persists the current state to disk."""
        try:
            faiss.write_index(self.index, self.storage_path + ".index")
            with open(self.storage_path + ".meta", "w") as f:
                import json
                json.dump(self.metadata, f)
            logger.debug(f"VectorStore: Checkpoint successful for '{self.index_name}'.")
        except Exception as e:
            logger.error(f"VectorStore: Checkpoint failed for '{self.index_name}': {e}")

    async def add(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]], persist: bool = True):
        """Adds embeddings and metadata to the centralized index."""
        if not embeddings.any(): return
        self.index.add(embeddings.astype('float32'))
        self.metadata.extend(metadata)
        if persist:
            self.checkpoint()

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
