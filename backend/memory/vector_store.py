"""
Sovereign Vector Store v8.
Handles persistent semantic memory using FAISS and local/cloud embedding sync.
Refactored into Autonomous Memory Ecosystem.
"""

import logging
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any

from backend.db.vector_store import VectorDB
from backend.core.security.user_kms import user_kms
from backend.db.postgres import PostgresDB
from backend.db.models import UserFact

logger = logging.getLogger(__name__)

# --- Vector Constants ---
FACT_DEDUPLICATION_THRESHOLD = 0.88 

class SovereignVectorStore:
    """
    LeviBrain v8: Tier 3 (Semantic Memory).
    Persistent vector search and deduplication.
    """

    @staticmethod
    async def get_user_memory(user_id: str) -> VectorDB:
        return await VectorDB.get_user_collection(user_id, "memory")

    @staticmethod
    async def get_global_memory() -> VectorDB:
        return await VectorDB.get_collection("global")

    @staticmethod
    async def store_fact(user_id: str, fact_text: str, category: str = "factual", importance: float = 0.5, success_impact: float = 0.5, 
                   usage_score: float = 1.0, recency_score: float = 1.0):
        """Standardized fact storage with FAISS deduplication, cloud backup, and Step 1.4 scoring."""
        if not user_id or not fact_text: return

        try:
            # 1. Access Vector Index
            user_memory = await SovereignVectorStore.get_user_memory(user_id)
            
            # 2. Local Deduplication
            existing = await user_memory.search(fact_text, limit=1)
            if existing and existing[0]["score"] > FACT_DEDUPLICATION_THRESHOLD:
                if existing[0].get("user_id") == user_id:
                    logger.info(f"FAISS Deduplication: fact exists for {user_id}")
                    return

            # 3. Create Record & Encrypt for Cloud
            fact_id = hashlib.md5(fact_text.encode()).hexdigest()
            encrypted_fact = await user_kms.encrypt_for_user(user_id, fact_text)
            
            doc_data = {
                "user_id": user_id,
                "fact": encrypted_fact,
                "category": category,
                "fact_id": f"{user_id}_{fact_id}", 
                "importance": importance,
                "success_impact": success_impact,
                "usage_score": usage_score,
                "recency_score": recency_score,
                "access_count": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # 4. Add to Local FAISS (Keep raw text for searching local index)
            await user_memory.add([fact_text], [doc_data])
            
            # 5. Persist to Postgres (Tier 3: SQL Resonance - Source of Truth)
            async with PostgresDB._session_factory() as session:
                new_fact = UserFact(
                    user_id=user_id,
                    fact=encrypted_fact,
                    category=category,
                    importance=importance,
                    is_deleted=False
                )
                session.add(new_fact)
                await session.commit()
                await session.refresh(new_fact)
                # Update meta with the official DB ID
                await user_memory.update_metadata("fact_id", doc_data["fact_id"], {"db_id": new_fact.id})

            logger.info(f"[VectorStore] Fact synchronized: FAISS + Postgres ({new_fact.id})")

        except Exception as e:
            logger.error(f"Vector Store insertion failed: {e}")

    @staticmethod
    async def search_facts(user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Semantic search with categorized weighting and recency bias."""
        if not user_id: return []
        
        try:
            # 1. FAISS Search
            user_memory = await SovereignVectorStore.get_user_memory(user_id)
            all_results = await user_memory.search(query, limit=20)
            
            # 2. Weighting, Decryption, and Step 1.4 Scoring
            user_facts = []
            now = datetime.now(timezone.utc)
            for res in all_results:
                if res.get("user_id") == user_id and res.get("score", 0) > 0.4:
                    # Calculate Recency Score (Decay over 30 days)
                    created_at = datetime.fromisoformat(res.get("created_at", now.isoformat()))
                    delta_days = (now - created_at).days
                    recency = max(0, 1.0 - (delta_days / 30.0))
                    
                    weight = 1.0
                    cat = res.get("category", "factual")
                    if cat == "preference": weight = 1.4
                    elif cat == "trait": weight = 1.3
                    
                    # Decrypt fact for synthesis
                    raw_fact = await user_kms.decrypt_for_user(user_id, res.get("fact", ""))
                    res["fact"] = raw_fact
                    
                    # Final Score: importance * usage * recency * base_score
                    usage = res.get("usage_score", 1.0)
                    importance = res.get("importance", 0.5)
                    
                    res["final_score"] = res["score"] * weight * (1.0 + importance) * (0.5 + recency * 0.5) * (0.8 + usage * 0.2)
                    res["recency_score"] = recency
                    user_facts.append(res)
                    
                    # Update usage count in background
                    usage_inc = usage + 0.05
                    res["usage_score"] = usage_inc
                    
                    # Persist usage update
                    if "fact_id" in res:
                        asyncio.create_task(user_memory.update_metadata("fact_id", res["fact_id"], {"usage_score": usage_inc}))

            user_facts.sort(key=lambda x: x["final_score"], reverse=True)
            return user_facts[:limit]

        except Exception as e:
            logger.error(f"Vector search anomaly: {e}")
            return []

    @staticmethod
    async def reindex_user_memory(user_id: str):
        """
        Sovereign v14.2: High-fidelity memory re-indexing.
        Pulls facts from MongoDB and rebuilds the local FAISS index to ensure consistency.
        """
        if not user_id: return
        
        logger.info(f"[VectorStore] Starting memory re-indexing for {user_id}...")
        try:
            from sqlalchemy import select
            async with PostgresDB._session_factory() as session:
                stmt = select(UserFact).where(UserFact.user_id == user_id, UserFact.is_deleted == False)
                res = await session.execute(stmt)
                facts_to_index = res.scalars().all()
            
            if not facts_to_index:
                logger.info(f"[VectorStore] No facts found in Postgres for {user_id}. Clearing local index.")
                user_memory = await SovereignVectorStore.get_user_memory(user_id)
                await user_memory.clear()
                return

            # 2. Decrypt and prepare texts and metadatas
            texts = []
            metadatas = []
            for fact_obj in facts_to_index:
                try:
                    # Decrypt and prepare texts and metadatas
                    raw_fact = await user_kms.decrypt_for_user(user_id, fact_obj.fact)
                    if raw_fact:
                        texts.append(raw_fact)
                        metadatas.append({
                            "user_id": user_id,
                            "fact": fact_obj.fact,
                            "category": fact_obj.category,
                            "importance": fact_obj.importance,
                            "db_id": fact_obj.id,
                            "fact_id": f"{user_id}_{hashlib.md5(raw_fact.encode()).hexdigest()}",
                            "created_at": fact_obj.created_at.isoformat()
                        })
                except Exception as dec_err:
                    logger.warning(f"[VectorStore] Failed to decrypt fact {fact_obj.id} during re-index: {dec_err}")

            # 3. Perform a Hard Rebuild of the FAISS collection
            if texts:
                user_memory = await SovereignVectorStore.get_user_memory(user_id)
                # Clear and batch add
                await user_memory.clear()
                await user_memory.add(texts, metadatas)
                logger.info(f"[VectorStore] Successfully re-indexed {len(texts)} facts for {user_id}.")

        except Exception as e:
            logger.error(f"[VectorStore] Re-indexing failed for {user_id}: {e}")

    @staticmethod
    async def reindex_global_memory():
        """
        Sovereign v14.2: Global memory re-indexing.
        Ensures common knowledge is synchronized across all nodes from MongoDB.
        """
        logger.info("[VectorStore] Starting global knowledge re-indexing...")
        try:
            from backend.db.mongo import MongoDB
            db = await MongoDB.get_db()
            if db is None: return

            cursor = db.global_facts.find({})
            facts_to_index = await cursor.to_list(length=1000)
            
            texts = []
            metadatas = []
            for doc in facts_to_index:
                doc.pop("_id", None)
                fact_text = doc.get("input") or doc.get("text")
                if fact_text:
                    texts.append(fact_text)
                    metadatas.append(doc)

            if texts:
                global_memory = await SovereignVectorStore.get_global_memory()
                await global_memory.clear()
                await global_memory.add(texts, metadatas)
                logger.info(f"[VectorStore] Successfully synchronized {len(texts)} global knowledge atoms.")

        except Exception as e:
            logger.error(f"[VectorStore] Global re-indexing failed: {e}")

    # --- Global Wisdom logic ---
    @staticmethod
    async def store_global_wisdom(input_text: str, output_text: str, mood: str):
        try:
            data = {
                "input": input_text[:300],
                "output": output_text[:600],
                "mood": mood,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            global_memory = await SovereignVectorStore.get_global_memory()
            await global_memory.add([input_text], [data])
        except Exception as e:
            logger.error(f"Global wisdom failure: {e}")
    @staticmethod
    async def delete_fact(user_id: str, fact_id: str):
        """
        Sovereign v14.2: Targeted memory pruning.
        Removes a fact from the local FAISS index by marking it as deleted and 
        eventually rebuilding (or using mask-based filtering).
        """
        if not user_id or not fact_id: return
        
        try:
            user_memory = await SovereignVectorStore.get_user_memory(user_id)
            # 1. Identify index of fact in metadata
            indices_to_remove = []
            for i, meta in enumerate(user_memory.metadata):
                if meta.get("fact_id") == fact_id:
                    indices_to_remove.append(i)
            
            if indices_to_remove:
                # 2. Trigger Remove Indices (Marks as deleted)
                await user_memory.remove_indices(indices_to_remove, hard_delete=False)
                logger.info(f"[VectorStore] Fact {fact_id} marked for deletion in {user_id}'s memory.")
        except Exception as e:
            logger.error(f"[VectorStore] Fact deletion failed for {user_id}/{fact_id}: {e}")

    @staticmethod
    async def get_all_facts(user_id: str) -> List[Dict[str, Any]]:
        """
        Sovereign v15.1: Full semantic retrieval for resonance hygiene.
        Directly pulls the metadata array for the user's local FAISS index.
        """
        user_memory = await SovereignVectorStore.get_user_memory(user_id)
        if not user_memory.metadata:
            return []
        
        # We return deep copies to prevent side-effects during decay processing
        import copy
        return [copy.deepcopy(m) for m in user_memory.metadata if not m.get("deleted")]

    @staticmethod
    async def sync_from_facts(user_id: str, facts: List[Dict[str, Any]]):
        """
        Sovereign v15.1: Atomic Semantic Hard-Sync.
        Used by the hygiene engine to commit pruned resonance patterns.
        """
        logger.info(f"🔄 [VectorStore] Hard-syncing resonance truth for {user_id} ({len(facts)} atoms)...")
        user_memory = await SovereignVectorStore.get_user_memory(user_id)
        
        texts = []
        metadatas = []
        for f in facts:
            # We need the raw text to rebuild the index
            text = f.get("text")
            if text:
                texts.append(text)
                metadatas.append(f)
        
        # Perform atomic hard-rebuild
        await user_memory.clear()
        if texts:
            await user_memory.add(texts, metadatas)
        
        logger.info(f"✨ [VectorStore] Resonance hygiene complete for {user_id}.")

    @staticmethod
    async def clear_user_memory(user_id: str):
        """Absolute wipe of a user's semantic local cache."""
        try:
            user_memory = await SovereignVectorStore.get_user_memory(user_id)
            await user_memory.clear()
            logger.info(f"[VectorStore] Hard-cleared local FAISS index for {user_id}")
        except Exception as e:
            logger.error(f"[VectorStore] Clear failed for {user_id}: {e}")

    @staticmethod
    async def monitor_drift(user_id: str) -> Dict[str, Any]:
        """
        Sovereign v16.2: Embedding Drift Monitoring.
        Detects if semantic clusters are migrating away from the core truth.
        """
        try:
            user_memory = await SovereignVectorStore.get_user_memory(user_id)
            if not user_memory.index or user_memory.index.ntotal < 10:
                return {"drift_detected": False, "score": 0.0}

            # 1. Fetch random samples to compute current centroid
            import numpy as np
            count = user_memory.index.ntotal
            samples = np.random.choice(count, min(count, 50), replace=False)
            vectors = [user_memory.index.reconstruct(int(i)) for i in samples]
            current_centroid = np.mean(vectors, axis=0)

            # 2. Compare with 'Anchor Centroid' from 24h ago (stored in Redis)
            from backend.db.redis import r as redis_client
            anchor_key = f"mcm:centroid:anchor:{user_id}"
            anchor_raw = redis_client.get(anchor_key)
            
            if not anchor_raw:
                # First run: establish baseline
                redis_client.setex(anchor_key, 86400 * 7, current_centroid.tobytes())
                return {"drift_detected": False, "score": 0.0, "status": "baseline_established"}

            anchor_centroid = np.frombuffer(anchor_raw, dtype=np.float32)
            cosine_sim = np.dot(current_centroid, anchor_centroid) / (np.linalg.norm(current_centroid) * np.linalg.norm(anchor_centroid))
            drift_score = 1.0 - cosine_sim

            DRIFT_THRESHOLD = 0.15 # 15% deviation
            if drift_score > DRIFT_THRESHOLD:
                logger.warning(f"⚠️ [MCM-T3] Significant Semantic Drift Detected for {user_id}: {drift_score:.4f}")
                # Trigger re-index event
                asyncio.create_task(SovereignVectorStore.reindex_user_memory(user_id))
                return {"drift_detected": True, "score": drift_score}

            return {"drift_detected": False, "score": drift_score}
        except Exception as e:
            logger.error(f"[VectorStore] Drift monitor failure: {e}")
            return {"drift_detected": False, "error": str(e)}

