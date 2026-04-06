import json
import logging
import hashlib
import os
import asyncio
import numpy as np
import faiss  # type: ignore
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from backend.db.vector_store import embed_text
from backend.db.postgres import PostgresDB
from backend.db.models import UserFact, Mission
from backend.db.vector_store import VectorDB
from backend.db.vector_store import SovereignVault

logger = logging.getLogger(__name__)

# --- Configuration ---
FACT_DEDUPLICATION_THRESHOLD = 0.88 
FACT_EXPIRY_DAYS = 90 # Extended for v6
# Final Production Paths
VECTOR_BASE = os.getenv("VECTOR_DB_PATH", "backend/data/vector_db")
FAISS_USER_INDEX = os.path.join(VECTOR_BASE, "user_faiss.bin")
FAISS_USER_META = os.path.join(VECTOR_BASE, "user_meta.json")
FAISS_GLOBAL_INDEX = os.path.join(VECTOR_BASE, "global_faiss.bin")
FAISS_GLOBAL_META = os.path.join(VECTOR_BASE, "global_meta.json")

# ─────────────────────────────────────────────────────────────────────────────
# FAISS ENGINE (Persistent Memory)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# FAISS ENGINE (Persistent Memory)
# ─────────────────────────────────────────────────────────────────────────────

async def get_user_memory(user_id: str) -> VectorDB:
    return await VectorDB.get_user_collection(user_id, "memory")

async def get_global_memory() -> VectorDB:
    return await VectorDB.get_collection("global")

# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────────────────────────

async def extract_memory_graph(user_input: str, bot_response: str) -> Dict[str, Any]:
    """
    Sovereign v8.6: Hybrid Memory Extraction.
    Identifies flat atomic facts for FAISS and Relation Triplets for Neo4j.
    """
    from .planner import call_lightweight_llm
    
    system_prompt = (
        "You are the LEVI Memory & Graph Extractor. Analyze the interaction and extract:\n"
        "1. Atomic Facts: [{\"fact\": \"...\", \"category\": \"preference|trait|history|factual\"}]\n"
        "2. Knowledge Triplets: [{\"subject\": \"...\", \"relation\": \"...\", \"object\": \"...\"}]\n\n"
        "Identify explicit relationships between the user, projects, technologies, and concepts.\n"
        "Output ONLY JSON: {\"facts\": [...], \"triplets\": [...]}"
    )
    user_prompt = f"User: {user_input}\nLEVI: {bot_response}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    raw_json = await call_lightweight_llm(messages)
    if not raw_json: return {"facts": [], "triplets": []}
    
    try:
        content = raw_json.strip()
        if "```json" in content: content = content.split("```json")[1].split("```")[0]
        elif "```" in content: content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())
    except Exception as e:
        logger.error(f"Failed to parse memory graph extraction: {e}")
        return {"facts": [], "triplets": []}

async def store_facts(user_id: str, new_facts: List[Dict[str, Any]]):
    """
    Sovereign Fact Storage with FAISS deduplication and Postgres persistence.
    """
    if not user_id or not new_facts: return

    for item in new_facts:
        fact_text = item.get("fact")
        category = item.get("category", "factual")
        importance = item.get("importance", 0.5)
        if not fact_text: continue

        try:
            # 1. Access Vector Store (Tier 3: HNSW/FAISS)
            user_memory = await get_user_memory(user_id)
            
            # 2. Local FAISS Deduplication
            existing = await user_memory.search(fact_text, limit=1)
            if existing and existing[0]["score"] > FACT_DEDUPLICATION_THRESHOLD:
                if existing[0].get("user_id") == user_id:
                    logger.info(f"FAISS: Deduplicated fact '{fact_text[:30]}...'")
                    continue

            # 3. Encrypt and persist to Postgres (Tier 3: SQL Resonance)
            # We keep the raw text for the local FAISS index but encrypt metadata for sovereignty
            encrypted_fact = SovereignVault.encrypt(fact_text)
            
            async with PostgresDB._session_factory() as session:
                new_fact = UserFact(
                    user_id=user_id,
                    fact=encrypted_fact,
                    category=category,
                    importance=importance
                )
                session.add(new_fact)
                await session.commit()
                await session.refresh(new_fact)
                fact_id = new_fact.id

            # 4. Add to Local Vector Index (Tier 3: HNSW / Tier 4: Identity)
            meta_data = {
                "user_id": user_id,
                "fact": encrypted_fact,
                "category": category,
                "importance": importance,
                "db_id": fact_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await user_memory.add([fact_text], [meta_data])
            
            logger.info(f"Fact '{fact_text[:20]}...' synchronized: Postgres ({fact_id}) + Vector Store")

        except Exception as e:
            logger.error(f"Error storing fact for user {user_id}: {e}")

async def search_relevant_facts(user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Perform high-speed semantic search for relevant user facts via FAISS.
    """
    if not user_id: return []
    
    try:
        # 1. Embed Query
        query_embedding = await asyncio.to_thread(embed_text, query)

        # 2. Search FAISS
        # 2. Search FAISS
        user_memory = await get_user_memory(user_id)
        all_results = await user_memory.search(query, limit=20)
        
        # 3. Filter by User-ID & Score
        user_facts = []
        for res in all_results:
            if res.get("user_id") == user_id and res.get("score", 0) > 0.4:
                # Recency bias logic
                weight = 1.0
                cat = res.get("category", "factual")
                if cat == "preference": weight = 1.4
                elif cat == "trait": weight = 1.3
                
                # LEVI v6: Decrypt fact if it was stored encrypted
                raw_fact = SovereignVault.decrypt(res.get("fact", ""))
                res["fact"] = raw_fact
                
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

async def garbage_collect_index(user_id: str):
    """
    Long-term maintenance: Purges expired or low-importance memories from FAISS.
    Rebuilds the index to maintain performance.
    """
    user_memory = await get_user_memory(user_id)
    if not user_memory.metadata: return

    async with user_memory._lock:
        now = datetime.now(timezone.utc)
        expiry_delta = timedelta(days=FACT_EXPIRY_DAYS)
        
        new_metadata = []
        new_embeddings = []
        
        # 1. Filter Metadata & Track Indices
        for i, meta in enumerate(user_memory.metadata):
            created_at = datetime.fromisoformat(meta["created_at"])
            importance = meta.get("importance", 0.5)
            
            # Pruning logic: 
            # - Keep if within 90 days
            # - Keep if importance > 0.8 regardless of age (Core Traits)
            if (now - created_at < expiry_delta) or (importance > 0.8):
                new_metadata.append(meta)
                try:
                    vec = user_memory.index.reconstruct(i)
                    new_embeddings.append(vec)
                except Exception: continue

        if len(new_metadata) == len(user_memory.metadata):
            logger.info("FAISS GC: No records pruned.")
            return

        # 2. Rebuild Index
        new_index = faiss.IndexFlatIP(384)
        if new_embeddings:
            new_index.add(np.array(new_embeddings).astype('float32'))
        
        user_memory.index = new_index
        user_memory.metadata = new_metadata
        
        # 3. Save to Disk
        user_memory._save()
        
        logger.info(f"FAISS GC Complete: Pruned {len(user_memory.metadata) - len(new_metadata)} records.")

async def store_global_wisdom(input_text: str, output_text: str, mood: str):
    """Stores a successful pattern in the Global FAISS Index and Postgres."""
    try:
        data = {
            "input": input_text[:300],
            "output": output_text[:600],
            "mood": mood,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        global_memory = await get_global_memory()
        await global_memory.add([input_text], [data])
        
        # In v13.1, global wisdom can be tracked via a public missions/patterns table if needed.
        # For now, we stop using Firestore.
    except Exception as e:
        logger.error(f"Global wisdom storage failed: {e}")

async def retrieve_resonant_patterns(query: str, limit: int = 2) -> List[Dict[str, str]]:
    """Retrieves resonant success patterns from Global FAISS Index."""
    try:
        global_memory = await get_global_memory()
        patterns = await global_memory.search(query, limit)
        return [{"input": p["input"], "output": p["output"]} for p in patterns if p.get("score", 0) > 0.8]
    except Exception as e:
        logger.error(f"Global pattern retrieval failed: {e}")
        return []
