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

from backend.db.vector_store import VectorDB, SovereignVault
from backend.db.firestore_db import db as firestore_db

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
    async def store_fact(user_id: str, fact_text: str, category: str = "factual", importance: float = 0.5, success_impact: float = 0.5):
        """Standardized fact storage with FAISS deduplication and cloud backup (v11.0)."""
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
            encrypted_fact = SovereignVault.encrypt(fact_text)
            
            doc_data = {
                "user_id": user_id,
                "fact": encrypted_fact,
                "category": category,
                "fact_id": f"{user_id}_{fact_id}", 
                "importance": importance,
                "success_impact": success_impact,
                "access_count": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # 4. Add to Local FAISS (Keep raw text for searching local index)
            await user_memory.add([fact_text], [doc_data])
            
            # 5. Backup to MongoDB (Prod Engine) & Firestore (Legacy)
            from backend.db.mongo import MongoDB
            db = await MongoDB.get_db()
            if db is not None:
                from backend.utils.runtime_tasks import create_tracked_task
                create_tracked_task(db.user_facts.insert_one(doc_data), name=f"vector-mongo-backup-{user_id}")
            
            from backend.utils.runtime_tasks import create_tracked_task
            create_tracked_task(asyncio.to_thread(
                lambda: firestore_db.collection("user_facts").document(doc_data["fact_id"]).set(doc_data)
            ), name=f"vector-firestore-backup-{user_id}")

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
            
            # 2. Weighting & Decryption
            user_facts = []
            for res in all_results:
                if res.get("user_id") == user_id and res.get("score", 0) > 0.4:
                    weight = 1.0
                    cat = res.get("category", "factual")
                    if cat == "preference": weight = 1.4
                    elif cat == "trait": weight = 1.3
                    
                    # Decrypt fact for synthesis
                    raw_fact = SovereignVault.decrypt(res.get("fact", ""))
                    res["fact"] = raw_fact
                    res["final_score"] = res["score"] * weight * (1.0 + res.get("importance", 0.5))
                    user_facts.append(res)

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
            from backend.db.mongo import MongoDB
            db = await MongoDB.get_db()
            if db is None:
                logger.error("[VectorStore] MongoDB unavailable for re-indexing.")
                return

            # 1. Fetch all facts for this user from the primary store
            cursor = db.user_facts.find({"user_id": user_id})
            facts_to_index = await cursor.to_list(length=1000)
            
            if not facts_to_index:
                logger.info(f"[VectorStore] No facts found in database for {user_id}. Clearing local index.")
                user_memory = await SovereignVectorStore.get_user_memory(user_id)
                await user_memory.clear()
                return

            # 2. Decrypt and prepare texts and metadatas
            texts = []
            metadatas = []
            for doc in facts_to_index:
                try:
                    # Remove MongoDB _id before storing in FAISS metadata
                    doc.pop("_id", None)
                    raw_fact = SovereignVault.decrypt(doc.get("fact", ""))
                    if raw_fact:
                        texts.append(raw_fact)
                        metadatas.append(doc)
                except Exception as dec_err:
                    logger.warning(f"[VectorStore] Failed to decrypt fact {doc.get('fact_id')} during re-index: {dec_err}")

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
