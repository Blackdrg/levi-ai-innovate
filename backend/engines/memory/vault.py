import logging
import os
import numpy as np
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MemoryVault:
    """
    Sovereign Memory Vault (SMV) v7.
    Hierarchical Memory System:
    1. Working Memory (Recent History)
    2. Long-Term Memory (Traits, Preferences via Firestore)
    3. Semantic Memory (Vectorized Archive via local FAISS)
    """

    def __init__(self, user_id: str, dimension: int = 384):
        self.user_id = user_id
        self.dimension = dimension
        self.index_path = f"backend/data/memory/{user_id}/faiss_index.bin"
        self.metadata_path = f"backend/data/memory/{user_id}/metadata.jsonl"
        self._initialize_vault()

    def _initialize_vault(self):
        """Lazy-load or initialize a FAISS index for the specific user."""
        import faiss
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        
        if os.path.exists(self.index_path):
            try:
                self.index = faiss.read_index(self.index_path)
                logger.info(f"Loaded existing FAISS index for {self.user_id}")
            except Exception as e:
                logger.error(f"FAISS load failure for {self.user_id}: {e}")
                self.index = faiss.IndexFlatL2(self.dimension)
        else:
            self.index = faiss.IndexFlatL2(self.dimension)
            logger.info(f"Initialized new FAISS index for {self.user_id}")

    async def store(self, content: str, embedding: List[float], metadata: Dict[str, Any] = None):
        """Append a new memory fragment to the vault."""
        import faiss
        vector = np.array([embedding]).astype('float32')
        self.index.add(vector)
        
        # Save Metadata
        ts = datetime.utcnow().isoformat()
        final_meta = metadata or {}
        final_meta.update({"content": content, "timestamp": ts})
        
        with open(self.metadata_path, "a", encoding="utf-8") as f:
            import json
            f.write(json.dumps(final_meta) + "\n")
            
        # Commit index to disk periodically (background)
        asyncio.create_task(self._commit_index())

    async def _commit_index(self):
        """Persist FAISS index to disk."""
        import faiss
        try:
            faiss.write_index(self.index, self.index_path)
        except Exception as e:
            logger.error(f"Memory commit failure: {e}")

    async def recall_semantic(self, embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top-k relevant fragments via vector search."""
        import faiss
        if self.index.ntotal == 0:
            return []

        vector = np.array([embedding]).astype('float32')
        distances, indices = self.index.search(vector, top_k)
        
        # Load metadata and filter matches
        results = []
        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                all_meta = [json.loads(line) for line in f]
                for i, idx in enumerate(indices[0]):
                    if idx != -1 and idx < len(all_meta):
                        meta = all_meta[idx]
                        meta["distance"] = float(distances[0][i])
                        results.append(meta)
        except Exception as e:
            logger.error(f"Recall metadata failure: {e}")
            
        return results

    @staticmethod
    async def get_combined_context(user_id: str, query: str = "") -> Dict[str, Any]:
        """High-level static method to bridge with the Orchestrator."""
        try:
            vault = MemoryVault(user_id)
            
            # 1. Semantic Recall (Requires Embedding)
            # For now, we use a mock embedding if the global one isn't imported
            mock_embedding = [0.1] * 384
            semantic_results = await vault.recall_semantic(mock_embedding, top_k=3)
            
            # 2. Long-Term Trait Lookup (Firestore Simulation for v7)
            # In a real environment, this would call sovereign_db
            traits = ["analytical", "curious", "philosophical"]
            preferences = ["concise", "deep-reasoning"]
            
            return {
                "user_id": user_id,
                "query": query,
                "semantic_results": semantic_results,
                "long_term": {
                    "traits": traits,
                    "preferences": preferences
                },
                "status": "synchronized"
            }
        except Exception as e:
            logger.error(f"Combined context retrieval failure: {e}")
            return {"user_id": user_id, "semantic_results": [], "long_term": {}, "error": str(e)}
