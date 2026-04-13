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

    def __init__(self, collection_name: str, dimension: int = 768, user_id: Optional[str] = None):
        self.collection_name = collection_name
        self.user_id = user_id
        self.dimension = dimension
        # v13.0 Model Specification
        from backend.embeddings import MODEL_PATH
        self.model_name = MODEL_PATH
        
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
        self._is_rebuilding = False
        self._write_queue: List[tuple[List[str], List[Dict[str, Any]]]] = []
        os.makedirs(self.storage_dir, exist_ok=True)

    @classmethod
    async def get_collection(cls, name: str, dimension: int = 768) -> 'VectorDB':
        """Get or create a global collection."""
        async with cls._lock:
            if name not in cls._instances:
                instance = cls(name, dimension)
                await instance._load()
                cls._instances[name] = instance
            return cls._instances[name]

    @classmethod
    async def get_user_collection(cls, user_id: str, name: str = "memory", dimension: int = 768) -> 'VectorDB':
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
        """Loads index and metadata with v13.0 integrity checks."""
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.meta_path, "r") as f:
                    data = json.load(f)
                    self.metadata = data.get("records", [])
                    
                    # v13.0 Model Integrity Check
                    stored_model = data.get("model_name")
                    if stored_model and stored_model != self.model_name:
                        logger.warning(f"[VectorDB] Model Mismatch for {self.collection_name}! Index: {stored_model}, System: {self.model_name}")
                        # Auto-rebuild if deterministic (reversible)
                        if all("text" in m for m in self.metadata):
                            logger.info(f"[VectorDB] Re-indexing collection {self.collection_name}...")
                            await self.rebuild_index()
                        else:
                            logger.critical("[VectorDB] RE-INDEXING FAILED: No raw text found. Manual intervention required.")
                            raise ValueError("Deterministic re-indexing impossible: Text data missing in metadata.")
                            
                logger.info(f"Loaded collection '{self.collection_name}' with {len(self.metadata)} records.")
            except Exception as e:
                logger.error(f"Failed to load collection {self.collection_name}: {e}")

    async def rebuild_index(self):
        """
        Sovereign v14.1.0-Autonomous-SOVEREIGN: High-fidelity deterministic re-indexing.
        Applies rebuild_lock (IsRebuilding) to prevent write-loss during migration.
        """
        self._is_rebuilding = True
        if not self.metadata: 
            self._is_rebuilding = False
            return
        
        # Filtering: skip records marked as deleted for GDPR compliance
        self.metadata = [m for m in self.metadata if "text" in m and not m.get("deleted")]
        texts = [m["text"] for m in self.metadata]

        if not texts: return
        
        logger.info(f"[VectorDB] Commencing rebuild for {len(texts)} vectors with L2-normalization...")
        
        from backend.db.vector_store import embed_text
        new_embeddings = []
        for text in texts:
            emb = await asyncio.to_thread(embed_text, text)
            # L2-normalization for Cosine Similarity equivalence
            norm_emb = emb / np.linalg.norm(emb)
            new_embeddings.append(norm_emb)
            
        emb_np = np.array(new_embeddings).astype('float32')
        self.dimension = emb_np.shape[1]
        
        # Build new HNSW index
        new_index = faiss.IndexHNSWFlat(self.dimension, 32, faiss.METRIC_INNER_PRODUCT)
        new_index.hnsw.efConstruction = 200
        new_index.hnsw.efSearch = 64
        new_index.add(emb_np)
        
        async with self._lock:
            # Atomic Swap & Flush Write Queue
            self.index = new_index
            self._is_rebuilding = False
            
            if self._write_queue:
                logger.info(f"[VectorDB] Flushing {len(self._write_queue)} queued writes for {self.collection_name}...")
                # We recursively call add, but _is_rebuilding is false now
                for q_texts, q_metas in self._write_queue:
                    # We can't await inside a thread if we were in one, but here we are in an async def
                    await self.add(q_texts, q_metas)
                self._write_queue = []

            # Ensure version/tenant mapping
            for m in self.metadata:
                m["version"] = os.getenv("SOVEREIGN_VERSION", "v14.1.0-Autonomous-SOVEREIGN")
            self._save()
        logger.info(f"[VectorDB] Rebuild complete for {self.collection_name}.")

    async def add(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        if not texts: return
        
        if self._is_rebuilding:
            logger.info(f"[VectorDB] Rebuild in progress for {self.collection_name}. Queuing write...")
            self._write_queue.append((texts, metadatas))
            return
        
        embeddings = []
        from backend.db.vector_store import embed_text
        for text in texts:
            emb = await asyncio.to_thread(embed_text, text)
            # L2-normalization for Inner Product (Cosine)
            norm_emb = emb / np.linalg.norm(emb)
            embeddings.append(norm_emb)
        
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
                json.dump({
                    "model_name": self.model_name,
                    "dimension": self.dimension,
                    "records": self.metadata
                }, f, default=str)
                
            os.replace(temp_index, self.index_path)
            os.replace(temp_meta, self.meta_path)
            logger.info(f"Persisted collection '{self.collection_name}' to storage.")
        except Exception as e:
            logger.error(f"Persistence error for {self.collection_name}: {e}")

    async def search(self, query: str, limit: int = 5, min_score: float = 0.4, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        from backend.db.vector_store import embed_text
        query_emb = await asyncio.to_thread(embed_text, query)
        # L2-normalization for Inner Product (Cosine)
        norm_query = query_emb / np.linalg.norm(query_emb)
        query_np = np.array([norm_query]).astype('float32')
        
        if self.index.ntotal == 0: return []
        
        # We fetch more than 'limit' to allow for filtering
        search_limit = limit * 2 if tenant_id else limit
        scores, indices = self.index.search(query_np, search_limit)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.metadata):
                score = float(scores[0][i])
                if score >= min_score:
                    meta = self.metadata[idx].copy()
                    if meta.get("deleted"):
                        continue
                    # v13.0 Tenant Isolation
                    if tenant_id and meta.get("tenant_id") != tenant_id:
                        continue
                    meta["score"] = score
                    results.append(meta)
                    if len(results) >= limit: break
        return results

    async def remove_indices(self, indices: List[int], hard_delete: bool = False):
        """
        Sovereign v14.1.0: GDPR Compliance Pass.
        Marks vectors as deleted or triggers a hard-rebuild for immediate removal.
        """
        if not indices: return
        async with self._lock:
            for idx in indices:
                if 0 <= idx < len(self.metadata):
                    self.metadata[idx]["deleted"] = True
            
            if hard_delete:
                logger.info(f"[VectorDB] Triggering mandatory hard-delete rebuild for {self.collection_name}...")
                await self.rebuild_index()
            else:
                self._save()
                logger.info(f"Marked {len(indices)} records as purged in '{self.collection_name}'.")

    async def update_metadata(self, filter_attr: str, filter_val: Any, updates: Dict[str, Any]):
        """
        Updates metadata for records matching the filter.
        """
        async with self._lock:
            updated = False
            for meta in self.metadata:
                if meta.get(filter_attr) == filter_val:
                    for k, v in updates.items():
                        meta[k] = v
                    updated = True
            if updated:
                self._save()
            return updated

    async def clear(self):
        async with self._lock:
            # Using Inner Product for v14.0 finality
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata = []
            self._save()
            logger.info(f"Cleared collection '{self.collection_name}'.")
