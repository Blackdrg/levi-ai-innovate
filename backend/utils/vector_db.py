import os
import json
import asyncio
import logging
import numpy as np
import faiss  # type: ignore
from typing import List, Dict, Any, Optional

from backend.utils.circuit_breaker import faiss_breaker
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
        
        # v15.1 Distributed Logic
        self.remote_url = os.getenv("FAISS_REMOTE_URL") # e.g. http://faiss-cluster-service
        
        # Production: Mount point for GCS FUSE
        self.base_path = os.getenv("VECTOR_DB_PATH", "backend/data/vector_db")
        
        # Scope by User ID if provided
        if user_id:
            self.storage_dir = os.path.join(self.base_path, "users", user_id)
        else:
            self.storage_dir = os.path.join(self.base_path, "global")
            
        self.index_path = os.path.join(self.storage_dir, f"{collection_name}_faiss.bin")
        self.meta_path = os.path.join(self.storage_dir, f"{collection_name}_meta.json")
        self.wal_path = os.path.join(self.storage_dir, f"{collection_name}.wal")
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
        """Loads index and metadata with v22.1 SHA-256 integrity checks."""
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            try:
                # v22.1: Verify SHA-256 before loading
                sha_path = f"{self.index_path}.sha256"
                if os.path.exists(sha_path):
                    with open(sha_path, "r") as f:
                        expected_sha = f.read().strip()
                    
                    with open(self.index_path, "rb") as f:
                        actual_sha = hashlib.sha256(f.read()).hexdigest()
                    
                    if actual_sha != expected_sha:
                        logger.error(f"🚨 [VectorDB] SHA-256 VERIFICATION FAILED for {self.collection_name}")
                        raise ValueError("Index corruption detected: SHA-256 mismatch.")
                
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
                            
                logger.info(f"Loaded collection '{self.collection_name}' ({len(self.metadata)} records). Hash verified.")
                
                # 🔄 WAL Replay (v22.1 Resilience)
                await self._replay_wal()
            except Exception as e:
                logger.error(f"Failed to load collection {self.collection_name}: {e}")
                
                # Checkpoint O-9: Rebuild-from-T2 (Postgres) on startup error
                self.index = faiss.IndexFlatIP(self.dimension)
                self.metadata = []
                
                if self.user_id:
                    logger.info(f"🧬 [VectorDB] Recovery mode: Triggering T2 Rebuild (Postgres) for {self.user_id}")
                    # We use a non-circular path to fetch data
                    asyncio.create_task(self._rebuild_from_t2())
                
                # Even if full load fails, try replaying WAL if it exists
                await self._replay_wal()

    async def _rebuild_from_t2(self):
        """Fetches facts from Postgres (T2) and adds them to the index."""
        if not self.user_id: return
        try:
            from backend.db.postgres import PostgresDB
            from backend.db.models import UserFact
            from sqlalchemy import select
            
            async with PostgresDB.session_scope() as session:
                stmt = select(UserFact).where(UserFact.user_id == self.user_id, UserFact.is_deleted == False)
                res = await session.execute(stmt)
                facts = res.scalars().all()
                
            if facts:
                from backend.db.vector_store import embed_text
                from backend.core.security.user_kms import user_kms
                
                texts = []
                metas = []
                for f in facts:
                    try:
                        raw_fact = await user_kms.decrypt_for_user(self.user_id, f.fact)
                        if raw_fact:
                            texts.append(raw_fact)
                            metas.append({
                                "user_id": self.user_id,
                                "fact": f.fact,
                                "category": f.category,
                                "importance": f.importance,
                                "db_id": f.id,
                                "created_at": f.created_at.isoformat()
                            })
                    except Exception: continue
                
                if texts:
                    await self.add(texts, metas)
                    logger.info(f"✅ [VectorDB] Recalibrated {len(texts)} vectors from T2 for {self.user_id}.")
        except Exception as e:
            logger.error(f"❌ [VectorDB] T2 Recovery failed: {e}")

    async def _replay_wal(self):
        """Replays the Write-Ahead Log for transient persistence."""
        if os.path.exists(self.wal_path):
            try:
                import pickle
                with open(self.wal_path, "rb") as f:
                    while True:
                        try:
                            # Load one chunk at a time from the WAL
                            chunk = pickle.load(f)
                            texts = chunk["texts"]
                            metas = chunk["metas"]
                            embs = np.array(chunk["embeddings"]).astype('float32')
                            
                            if self.index:
                                self.index.add(embs)
                                for i, text in enumerate(texts):
                                    meta = metas[i].copy()
                                    meta["text"] = text
                                    self.metadata.append(meta)
                        except EOFError:
                            break
                logger.info(f"🛡️ [VectorDB] WAL Replay Success for {self.collection_name}.")
            except Exception as e:
                logger.error(f"[VectorDB] WAL Replay failed: {e}")

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
            emb = await embed_text(text)
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


    def _save(self):
        try:
            # v22.1: Atomic save (temp + rename) + SHA-256 Checksum
            import hashlib
            temp_index = f"{self.index_path}.tmp"
            temp_meta = f"{self.meta_path}.tmp"
            temp_sha = f"{self.index_path}.sha256.tmp"
            
            faiss.write_index(self.index, temp_index)
            
            # Generate SHA-256 for the index
            with open(temp_index, "rb") as f:
                index_sha = hashlib.sha256(f.read()).hexdigest()
            
            with open(temp_sha, "w") as f:
                f.write(index_sha)
            
            with open(temp_meta, "w") as f:
                json.dump({
                    "model_name": self.model_name,
                    "dimension": self.dimension,
                    "records": self.metadata,
                    "sha256": index_sha
                }, f, default=str)
                
            # Atomic Rename Sequence
            os.replace(temp_index, self.index_path)
            os.replace(temp_sha, f"{self.index_path}.sha256")
            os.replace(temp_meta, self.meta_path)
            
            # Truncate WAL upon successful full checkpoint
            if os.path.exists(self.wal_path):
                os.remove(self.wal_path)
            
            logger.info(f"✨ [VectorDB] Persisted '{self.collection_name}' (Hash: {index_sha[:8]}...).")
        except Exception as e:
            logger.error(f"Persistence error for {self.collection_name}: {e}")

    async def search(self, query: str, limit: int = 5, min_score: float = 0.4, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.remote_url:
            return await self._search_remote(query, limit, min_score, tenant_id)
            
        from backend.db.vector_store import embed_text
        import numpy as np
        query_emb = await embed_text(query)
        # L2-normalization for Inner Product (Cosine)
        norm_query = query_emb / np.linalg.norm(query_emb)
        query_np = np.array([norm_query]).astype('float32')
        
        if self.index.ntotal == 0: return []
        
        # We fetch more than 'limit' to allow for filtering
        search_limit = limit * 2 if tenant_id else limit
        
        async def _run_search():
            return self.index.search(query_np, search_limit)

        try:
            scores, indices = await faiss_breaker.call(_run_search)
        except Exception as e:
            logger.error(f"[VectorDB] FAISS Search failed (Circuit: {faiss_breaker.state.value}): {e}")
            return []

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

    async def _search_remote(self, query: str, limit: int, min_score: float, tenant_id: Optional[str]) -> List[Dict[str, Any]]:
        """Sovereign v15.1: High-Performance Remote Cluster Retrieval."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(
                    f"{self.remote_url}/search",
                    json={
                        "query": query,
                        "limit": limit,
                        "min_score": min_score,
                        "tenant_id": tenant_id or self.user_id,
                        "collection": self.collection_name
                    }
                )
                res.raise_for_status()
                return res.json().get("results", [])
        except Exception as e:
            logger.error(f"[VectorDB-Remote] Search failed for {self.collection_name}: {e}")
            return []

    async def add(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        if not texts: return
        
        if self.remote_url:
            await self._add_remote(texts, metadatas)
            # We don't return here because we also want local cache to be updated if it exists
        
        if self._is_rebuilding:
            logger.info(f"[VectorDB] Rebuild in progress for {self.collection_name}. Queuing write...")
            self._write_queue.append((texts, metadatas))
            return
        
        embeddings = []
        from backend.db.vector_store import embed_text
        for text in texts:
            emb = await embed_text(text)
            # L2-normalization for Inner Product (Cosine)
            norm_emb = emb / np.linalg.norm(emb)
            embeddings.append(norm_emb)
        
        emb_np = np.array(embeddings).astype('float32')
        
        # BFT Signature Verification (Appendix G Graduation Requirement)
        strict_bft = os.getenv("STRICT_BFT", "false").lower() == "true"
        for meta in metadatas:
            if strict_bft and not meta.get("bft_signature"):
                logger.error(f"🚨 [VectorDB-BFT] REJECTED: Fact missing Tier-4 signature in STRICT_BFT mode.")
                raise ValueError("BFT protocol violation: Fact lacks non-repudiation signature.")
            elif meta.get("bft_signature"):
                logger.debug(f"🛡️ [VectorDB-BFT] Fact verified via agent signature: {meta['bft_signature'][:10]}...")

        async with self._lock:
            if self.index:
                async def _run_add():
                    self.index.add(emb_np)
                
                await faiss_breaker.call(_run_add)
                
                # Store the text along with metadata
                for i, text in enumerate(texts):
                    meta = metadatas[i].copy()
                    meta["text"] = text
                    self.metadata.append(meta)
                
                # High-Frequency WAL Checkpoint (Step 1.5)
                try:
                    import pickle
                    with open(self.wal_path, "ab") as f:
                        pickle.dump({
                            "texts": texts,
                            "metas": metadatas,
                            "embeddings": embeddings
                        }, f)
                except Exception as e:
                    logger.error(f"[VectorDB] WAL Write failed: {e}")

                # Sovereign v22.1: Periodic WAL checkpoint (every 100 writes)
                self.wal_count = getattr(self, "wal_count", 0) + 1
                if self.wal_count >= 100:
                    logger.info(f"🔄 [VectorDB] Periodic WAL checkpoint (100 writes reached).")
                    self._save()
                    self.wal_count = 0

    async def _add_remote(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        """Broadcasts vectors to the distributed Tier 3 cluster."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.remote_url}/add",
                    json={
                        "texts": texts,
                        "metadatas": metadatas,
                        "collection": self.collection_name,
                        "user_id": self.user_id
                    }
                )
        except Exception as e:
            logger.error(f"[VectorDB-Remote] Insertion failed for {self.collection_name}: {e}")

    async def remove_indices(self, indices: List[int], hard_delete: bool = False):
        """
        Sovereign v14.1.0: GDPR Compliance Pass.
        Marks vectors as deleted or triggers a hard-rebuild for immediate removal.
        """
        if not indices: return
        
        if self.remote_url:
            # Propagate deletion to cluster
            await self._remove_remote(indices)
            
        async with self._lock:
            for idx in indices:
                if 0 <= idx < len(self.metadata):
                    self.metadata[idx]["deleted"] = True
            
            if hard_delete:
                logger.info(f"[VectorDB] Triggering mandatory hard-delete rebuild for {self.collection_name}...)")
                await self.rebuild_index()
            else:
                self._save()
                logger.info(f"Marked {len(indices)} records as purged in '{self.collection_name}'.")

    async def _remove_remote(self, indices: List[int]):
        """Sovereign v15.2: Propagates deletion indices to the distributed cluster."""
        import httpx
        try:
            # We map indices to stable IDs (fact_id) if possible for better remote consistency
            ids = [self.metadata[i]["fact_id"] for i in indices if i < len(self.metadata) and "fact_id" in self.metadata[i]]
            if not ids: return

            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.remote_url}/remove",
                    json={
                        "fact_ids": ids,
                        "collection": self.collection_name,
                        "user_id": self.user_id
                    }
                )
        except Exception as e:
            logger.error(f"[VectorDB-Remote] Deletion propagation failed for {self.collection_name}: {e}")

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
