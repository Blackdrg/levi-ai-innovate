import os
import json
import asyncio
import logging
import numpy as np
import faiss  # type: ignore
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class VectorDB:
    """
    Unified FAISS Vector Store for LEVI-AI.
    Supports multiple collections (memory, documents, global).
    """
    _instances: Dict[str, 'VectorDB'] = {}
    _lock = asyncio.Lock()

    def __init__(self, collection_name: str, dimension: int = 384, user_id: Optional[str] = None):
        self.collection_name = collection_name
        self.user_id = user_id
        self.dimension = dimension
        
        # Production: Mount point for GCS FUSE
        self.base_path = os.getenv("VECTOR_DB_PATH", "backend/data/vector_db")
        
        # Scope by User ID if provided
        if user_id:
            self.storage_dir = os.path.join(self.base_path, "users", user_id)
        else:
            self.storage_dir = os.path.join(self.base_path, "global")
            
        self.index_path = os.path.join(self.storage_dir, f"{collection_name}_faiss.bin")
        self.meta_path = os.path.join(self.storage_dir, f"{collection_name}_meta.json")
        self.index = None
        self.metadata: List[Dict[str, Any]] = []
        os.makedirs(self.storage_dir, exist_ok=True)

    @classmethod
    async def get_collection(cls, name: str, dimension: int = 384) -> 'VectorDB':
        """Get or create a global collection."""
        async with cls._lock:
            if name not in cls._instances:
                instance = cls(name, dimension)
                await instance._load()
                cls._instances[name] = instance
            return cls._instances[name]

    @classmethod
    async def get_user_collection(cls, user_id: str, name: str = "memory", dimension: int = 384) -> 'VectorDB':
        """Get or create a user-specific collection."""
        instance_key = f"user_{user_id}_{name}"
        async with cls._lock:
            if instance_key not in cls._instances:
                instance = cls(name, dimension, user_id=user_id)
                await instance._load()
                cls._instances[instance_key] = instance
                
                # Cleanup logic: If we have too many indices in RAM, clear old ones
                if len(cls._instances) > 50:
                    # Simple cleanup: remove the first few (oldest) entries
                    # In a real system, we'd use LRU or time-based expiry.
                    keys_to_remove = list(cls._instances.keys())[:10]
                    for k in keys_to_remove:
                        if k != instance_key:
                            del cls._instances[k]
                            
            return cls._instances[instance_key]

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
            # v10.0 Upgrade: Use HNSW for sub-30ms retrieval at scale
            # M=32 for high-speed production performance
            self.index = faiss.IndexHNSWFlat(self.dimension, 32)
            self.index.hnsw.efConstruction = 40
            self.index.hnsw.efSearch = 16
            self.metadata = []
            logger.info(f"Initialized new collection '{self.collection_name}' (HNSW v10.0).")

    async def add(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        if not texts: return
        
        embeddings = []
        from backend.db.vector_store import embed_text
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
        try:
            # Atomic save to prevent corruption on GCS FUSE/Persistent Storage
            temp_index = f"{self.index_path}.tmp"
            temp_meta = f"{self.meta_path}.tmp"
            
            faiss.write_index(self.index, temp_index)
            with open(temp_meta, "w") as f:
                json.dump(self.metadata, f, default=str)
                
            os.replace(temp_index, self.index_path)
            os.replace(temp_meta, self.meta_path)
            logger.info(f"Persisted collection '{self.collection_name}' to storage.")
        except Exception as e:
            logger.error(f"Persistence error for {self.collection_name}: {e}")

    async def search(self, query: str, limit: int = 5, min_score: float = 0.4) -> List[Dict[str, Any]]:
        from backend.db.vector_store import embed_text
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
                    if meta.get("deleted"):
                        continue
                    meta["score"] = score
                    results.append(meta)
        return results

    async def remove_indices(self, indices: List[int]):
        """
        Sovereign v9.8.1: Soft Purge.
        Marks vectors as deleted so they are ignored by the search logic.
        """
        if not indices: return
        async with self._lock:
            for idx in indices:
                if 0 <= idx < len(self.metadata):
                    self.metadata[idx]["deleted"] = True
            self._save()
            logger.info(f"Marked {len(indices)} records as purged in '{self.collection_name}'.")

    async def clear(self):
        async with self._lock:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata = []
            self._save()
            logger.info(f"Cleared collection '{self.collection_name}'.")
