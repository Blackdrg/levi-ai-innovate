import json
import logging
import hashlib
import os
import asyncio
import numpy as np
import faiss  # type: ignore
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from backend.embeddings import embed_text
from backend.firestore_db import db as firestore_db

logger = logging.getLogger(__name__)

# --- Configuration ---
FACT_DEDUPLICATION_THRESHOLD = 0.88 
FACT_EXPIRY_DAYS = 90 # Extended for v6
# Final Production Paths
FAISS_USER_INDEX = os.getenv("FAISS_INDEX_PATH", "backend/data/memory/user_faiss.bin")
FAISS_USER_META = os.getenv("FAISS_METADATA_PATH", "backend/data/memory/user_meta.json")
FAISS_GLOBAL_INDEX = os.getenv("FAISS_GLOBAL_PATH", "backend/data/memory/global_faiss.bin")
FAISS_GLOBAL_META = os.getenv("FAISS_GLOBAL_META", "backend/data/memory/global_meta.json")

# ─────────────────────────────────────────────────────────────────────────────
# FAISS ENGINE (Persistent Memory)
# ─────────────────────────────────────────────────────────────────────────────

class FaissMemory:
    """
    Persistent FAISS-powered vector memory for User Facts.
    """
    _index = None
    _metadata: List[Dict[str, Any]] = []
    _lock = asyncio.Lock()

    @classmethod
    async def _init_engine(cls):
        if cls._index is not None: return
        async with cls._lock:
            if cls._index is not None: return
            os.makedirs(os.path.dirname(FAISS_USER_INDEX), exist_ok=True)
            if os.path.exists(FAISS_USER_INDEX) and os.path.exists(FAISS_USER_META):
                try:
                    cls._index = faiss.read_index(FAISS_USER_INDEX)
                    with open(FAISS_USER_META, "r") as f: cls._metadata = json.load(f)
                except Exception: cls._index = None
            if cls._index is None:
                # Align with 'paraphrase-MiniLM-L6-v2' (384-dim)
                cls._index = faiss.IndexFlatIP(384)
                cls._metadata = []

    @classmethod
    async def add_record(cls, embedding: List[float], record_data: Dict[str, Any]):
        await cls._init_engine()
        async with cls._lock:
            emb_np = np.array([embedding]).astype('float32')
            cls._index.add(emb_np)
            cls._metadata.append(record_data)
            faiss.write_index(cls._index, FAISS_USER_INDEX)
            with open(FAISS_USER_META, "w") as f: json.dump(cls._metadata, f, default=str)

    @classmethod
    async def search(cls, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        await cls._init_engine()
        if cls._index.ntotal == 0: return []
        async with cls._lock:
            emb_np = np.array([query_embedding]).astype('float32')
            scores, indices = cls._index.search(emb_np, limit)
            results = []
            for i, idx in enumerate(indices[0]):
                if idx != -1 and idx < len(cls._metadata):
                    meta = cls._metadata[idx].copy()
                    meta["score"] = float(scores[0][i])
                    results.append(meta)
            return results

class GlobalPatternMemory:
    """
    Sovereign Global Wisdom Index. Stores anonymized success patterns.
    """
    _index = None
    _metadata: List[Dict[str, Any]] = []
    _lock = asyncio.Lock()

    @classmethod
    async def _init_engine(cls):
        if cls._index is not None: return
        async with cls._lock:
            if cls._index is not None: return
            os.makedirs(os.path.dirname(FAISS_GLOBAL_INDEX), exist_ok=True)
            if os.path.exists(FAISS_GLOBAL_INDEX) and os.path.exists(FAISS_GLOBAL_META):
                try:
                    cls._index = faiss.read_index(FAISS_GLOBAL_INDEX)
                    with open(FAISS_GLOBAL_META, "r") as f: cls._metadata = json.load(f)
                except Exception: cls._index = None
            if cls._index is None:
                cls._index = faiss.IndexFlatIP(384)
                cls._metadata = []

    @classmethod
    async def add_pattern(cls, embedding: List[float], pattern_data: Dict[str, Any]):
        await cls._init_engine()
        async with cls._lock:
            emb_np = np.array([embedding]).astype('float32')
            cls._index.add(emb_np)
            cls._metadata.append(pattern_data)
            faiss.write_index(cls._index, FAISS_GLOBAL_INDEX)
            with open(FAISS_GLOBAL_META, "w") as f: json.dump(cls._metadata, f, default=str)

    @classmethod
    async def search_patterns(cls, query_embedding: List[float], limit: int = 2) -> List[Dict[str, Any]]:
        await cls._init_engine()
        if cls._index.ntotal == 0: return []
        async with cls._lock:
            emb_np = np.array([query_embedding]).astype('float32')
            scores, indices = cls._index.search(emb_np, limit)
            results = []
            for i, idx in enumerate(indices[0]):
                if idx != -1 and idx < len(cls._metadata):
                    meta = cls._metadata[idx].copy()
                    meta["score"] = float(scores[0][i])
                    results.append(meta)
            return results

# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────────────────────────

async def extract_facts(user_input: str, bot_response: str) -> List[Dict[str, Any]]:
    """Uses LLM to extract categorized atomic facts about the user."""
    from backend.services.orchestrator.planner import call_lightweight_llm
    
    system_prompt = (
        "You are the LEVI Memory Extractor. Extract key, atomic facts about the user. "
        "Categorize each fact as: 'preference', 'trait', 'history', or 'factual'. "
        "Output ONLY a JSON array of objects: [{\"fact\": \"...\", \"category\": \"...\"}]. "
        "If no new facts are found, output []."
    )
    user_prompt = f"User: {user_input}\nLEVI: {bot_response}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    facts_json = await call_lightweight_llm(messages)
    if not facts_json: return []
    
    try:
        content = facts_json.strip()
        if "```json" in content: content = content.split("```json")[1].split("```")[0]
        elif "```" in content: content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())
    except Exception as e:
        logger.error(f"Failed to parse extracted facts: {e}")
        return []

async def store_facts(user_id: str, new_facts: List[Dict[str, Any]]):
    """
    Sovereign Fact Storage with FAISS deduplication.
    """
    if not user_id or not new_facts: return

    for item in new_facts:
        fact_text = item.get("fact")
        category = item.get("category", "factual")
        importance = item.get("importance", 0.5)
        if not fact_text: continue

        try:
            # 1. Embed Locally
            embedding = await asyncio.to_thread(embed_text, fact_text)
            
            # 2. Local Deduplication
            existing = await FaissMemory.search(embedding, limit=1)
            if existing and existing[0]["score"] > FACT_DEDUPLICATION_THRESHOLD:
                if existing[0].get("user_id") == user_id:
                    logger.info(f"FAISS: Deduplicated fact '{fact_text[:30]}...'")
                    continue

            # 3. Create Record
            fact_id = hashlib.md5(fact_text.encode()).hexdigest()
            doc_data = {
                "user_id": user_id,
                "fact": fact_text,
                "category": category,
                "fact_id": f"{user_id}_{fact_id}", 
                "importance": importance,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # 4. Add to Local VM
            await FaissMemory.add_record(embedding, doc_data)

            # 5. Backup to Firestore (Async Non-Blocking)
            asyncio.create_task(asyncio.to_thread(
                lambda: firestore_db.collection("user_facts").document(doc_data["fact_id"]).set(doc_data)
            ))

        except Exception as e:
            logger.error(f"Error storing fact: {e}")

async def search_relevant_facts(user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Perform high-speed semantic search for relevant user facts via FAISS.
    """
    if not user_id: return []
    
    try:
        # 1. Embed Query
        query_embedding = await asyncio.to_thread(embed_text, query)

        # 2. Search FAISS
        all_results = await FaissMemory.search(query_embedding, limit=20)
        
        # 3. Filter by User-ID & Score
        user_facts = []
        for res in all_results:
            if res.get("user_id") == user_id and res.get("score", 0) > 0.4:
                # Recency bias logic
                weight = 1.0
                cat = res.get("category", "factual")
                if cat == "preference": weight = 1.4
                elif cat == "trait": weight = 1.3
                
                res["final_score"] = res["score"] * weight * (1.0 + res.get("importance", 0.5))
                user_facts.append(res)

        user_facts.sort(key=lambda x: x["final_score"], reverse=True)
        return user_facts[:limit]

    except Exception as e:
        logger.error(f"Error searching relevant facts: {e}")
        return []

async def prune_old_facts(user_id: str):
    """
    Deprecated: Use consolidated garbage_collect_index.
    """
    pass

async def garbage_collect_index():
    """
    Long-term maintenance: Purges expired or low-importance memories from FAISS.
    Rebuilds the index to maintain performance.
    """
    await FaissMemory._init_engine()
    if not FaissMemory._metadata: return

    async with FaissMemory._lock:
        now = datetime.now(timezone.utc)
        expiry_delta = timedelta(days=FACT_EXPIRY_DAYS)
        
        new_metadata = []
        new_embeddings = []
        
        # 1. Filter Metadata & Track Indices
        for i, meta in enumerate(FaissMemory._metadata):
            created_at = datetime.fromisoformat(meta["created_at"])
            importance = meta.get("importance", 0.5)
            
            # Pruning logic: 
            # - Keep if within 90 days
            # - Keep if importance > 0.1 regardless of age (Core Traits)
            if (now - created_at < expiry_delta) or (importance > 0.8):
                new_metadata.append(meta)
                # Re-extract embedding (in a real system, we'd reconstruct from Index-ID if possible)
                # Since we don't have reconstruct() on FlatIP easily here, we'll assume a rebuild is needed.
                # However, FAISS IndexFlat does support reconstruction: index.reconstruct(i)
                try:
                    vec = FaissMemory._index.reconstruct(i)
                    new_embeddings.append(vec)
                except Exception: continue

        if len(new_metadata) == len(FaissMemory._metadata):
            logger.info("FAISS GC: No records pruned.")
            return

        # 2. Rebuild Index
        new_index = faiss.IndexFlatIP(384)
        if new_embeddings:
            new_index.add(np.array(new_embeddings).astype('float32'))
        
        FaissMemory._index = new_index
        FaissMemory._metadata = new_metadata
        
        # 3. Save to Disk
        faiss.write_index(FaissMemory._index, FAISS_USER_INDEX)
        with open(FAISS_USER_META, "w") as f:
            json.dump(FaissMemory._metadata, f, default=str)
        
        logger.info(f"FAISS GC Complete: Pruned {len(FaissMemory._metadata) - len(new_metadata)} records.")

async def store_global_wisdom(input_text: str, output_text: str, mood: str):
    """Stores a successful pattern in the Global FAISS Index."""
    try:
        embedding = await asyncio.to_thread(embed_text, input_text)
        data = {
            "input": input_text[:300],
            "output": output_text[:600],
            "mood": mood,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await GlobalPatternMemory.add_pattern(embedding, data)
        # Backup to Firestore
        pid = hashlib.md5(input_text.encode()).hexdigest()
        asyncio.create_task(asyncio.to_thread(
            lambda: firestore_db.collection("global_wisdom").document(pid).set(data)
        ))
    except Exception as e:
        logger.error(f"Global wisdom storage failed: {e}")

async def retrieve_resonant_patterns(query: str, limit: int = 2) -> List[Dict[str, str]]:
    """Retrieves resonant success patterns from Global FAISS Index."""
    try:
        embedding = await asyncio.to_thread(embed_text, query)
        patterns = await GlobalPatternMemory.search_patterns(embedding, limit)
        return [{"input": p["input"], "output": p["output"]} for p in patterns if p.get("score", 0) > 0.8]
    except Exception as e:
        logger.error(f"Global pattern retrieval failed: {e}")
        return []
