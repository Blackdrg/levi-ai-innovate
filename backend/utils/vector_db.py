import os
import json
import asyncio
import logging
import numpy as np
import faiss  # type: ignore
from typing import List, Dict, Any, Optional
from backend.embeddings import embed_text

logger = logging.getLogger(__name__)

class VectorDB:
    """
    Unified FAISS Vector Store for LEVI-AI.
    Supports multiple collections (memory, documents, global).
    """
    _instances: Dict[str, 'VectorDB'] = {}
    _lock = asyncio.Lock()

    def __init__(self, collection_name: str, dimension: int = 384):
        self.collection_name = collection_name
        self.dimension = dimension
        self.index_path = f"backend/data/vector_db/{collection_name}_faiss.bin"
        self.meta_path = f"backend/data/vector_db/{collection_name}_meta.json"
        self.index = None
        self.metadata: List[Dict[str, Any]] = []
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

    @classmethod
    async def get_collection(cls, name: str, dimension: int = 384) -> 'VectorDB':
        async with cls._lock:
            if name not in cls._instances:
                instance = cls(name, dimension)
                await instance._load()
                cls._instances[name] = instance
            return cls._instances[name]

    async def _load(self):
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.meta_path, "r") as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded collection '{self.collection_name}' with {len(self.metadata)} records.")
            except Exception as e:
                logger.error(f"Failed to load collection {self.collection_name}: {e}")
        
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata = []
            logger.info(f"Initialized new collection '{self.collection_name}'.")

    async def add(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        if not texts: return
        
        embeddings = []
        for text in texts:
            emb = await asyncio.to_thread(embed_text, text)
            embeddings.append(emb)
        
        emb_np = np.array(embeddings).astype('float32')
        
        async with self._lock:
            self.index.add(emb_np)
            # Store the text along with metadata
            for i, text in enumerate(texts):
                meta = metadatas[i].copy()
                meta["text"] = text
                self.metadata.append(meta)
            self._save()

    def _save(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w") as f:
            json.dump(self.metadata, f, default=str)

    async def search(self, query: str, limit: int = 5, min_score: float = 0.4) -> List[Dict[str, Any]]:
        query_emb = await asyncio.to_thread(embed_text, query)
        query_np = np.array([query_emb]).astype('float32')
        
        if self.index.ntotal == 0: return []
        
        scores, indices = self.index.search(query_np, limit)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.metadata):
                score = float(scores[0][i])
                if score >= min_score:
                    meta = self.metadata[idx].copy()
                    meta["score"] = score
                    results.append(meta)
        return results

    async def clear(self):
        async with self._lock:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata = []
            self._save()
            logger.info(f"Cleared collection '{self.collection_name}'.")
