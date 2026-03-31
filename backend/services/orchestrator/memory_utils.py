import json
import logging
import hashlib
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from backend.embeddings import embed_text, cosine_sim
from backend.firestore_db import db as firestore_db

logger = logging.getLogger(__name__)

# --- Configuration ---
FACT_DEDUPLICATION_THRESHOLD = 0.85 # Cosine similarity threshold for deduplication
FACT_EXPIRY_DAYS = 30 # Prune facts older than this

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
        if "```json" in facts_json:
            facts_json = facts_json.split("```json")[1].split("```")[0]
        elif "```" in facts_json:
            facts_json = facts_json.split("```")[1].split("```")[0]
        
        return json.loads(facts_json.strip())
    except Exception as e:
        logger.error(f"Failed to parse extracted facts: {e}")
        return []

import asyncio

# Redis buffer key pattern: mem_buffer:{user_id} → Redis List of JSON fact strings
MEMORY_BUFFER_MAX = 10  # Trigger immediate flush if buffer exceeds this size

async def _get_buffered_facts(user_id: str) -> list:
    """Read facts currently sitting in the Redis write buffer for deduplication."""
    from backend.redis_client import HAS_REDIS, r as redis_client
    if not HAS_REDIS:
        return []
    try:
        raw_items = redis_client.lrange(f"mem_buffer:{user_id}", 0, -1)
        return [json.loads(item) for item in raw_items]
    except Exception:
        return []

async def store_facts(user_id: str, new_facts: List[Dict[str, Any]]):
    """Embed and store facts with semantic deduplication.
    
    PHASE 47: Buffered Writes — facts are written to Redis first and flushed
    to Firestore every 30 seconds by the Celery Beat task (memory_tasks.py).
    This significantly reduces Firestore write costs under high traffic.
    """
    if not user_id or not new_facts: return
    from backend.redis_client import HAS_REDIS, r as redis_client

    # 1. Fetch existing Firestore facts for deduplication
    existing_docs = firestore_db.collection("user_facts") \
        .where("user_id", "==", user_id) \
        .stream()
    existing_facts = [doc.to_dict() for doc in existing_docs]

    # 2. Also include facts currently in the Redis buffer (not yet flushed)
    buffered_facts = await _get_buffered_facts(user_id)
    all_known_facts = existing_facts + buffered_facts

    newly_buffered = 0
    for item in new_facts:
        fact_text = item.get("fact")
        category = item.get("category", "factual")
        if not fact_text: continue

        try:
            new_embedding = await asyncio.to_thread(embed_text, fact_text)

            # 3. Deduplication check against Firestore + buffer
            is_duplicate = False
            for old_fact in all_known_facts:
                old_emb = np.array(old_fact.get("embedding", []))
                if old_emb.size > 0:
                    similarity = cosine_sim(np.array(new_embedding), old_emb)
                    if similarity > FACT_DEDUPLICATION_THRESHOLD:
                        logger.info(f"Deduplicated fact: '{fact_text}' matches existing '{old_fact.get('fact')}'")
                        is_duplicate = True
                        break

            if is_duplicate:
                continue

            # 4. Build fact payload (same shape as Firestore doc)
            import hashlib
            fact_id = hashlib.md5(fact_text.encode()).hexdigest()
            doc_data = {
                "user_id": user_id,
                "fact": fact_text,
                "category": category,
                "embedding": new_embedding,
                "fact_id": f"{user_id}_{fact_id}",  # Pre-compute Firestore doc ID
                "created_at": datetime.utcnow(),  # Native datetime for Firestore
            }

            if HAS_REDIS:
                # 5a. Buffer write: push to Redis list (O(1) operation)
                buffer_key = f"mem_buffer:{user_id}"
                redis_client.rpush(buffer_key, json.dumps(doc_data, default=str))
                redis_client.expire(buffer_key, 3600)  # Safety TTL: 1 hour
                newly_buffered += 1
                logger.info(f"Buffered new fact for user {user_id}: '{fact_text[:50]}'")
            else:
                # 5b. Fallback: direct Firestore write if Redis is unavailable
                await asyncio.to_thread(
                    firestore_db.collection("user_facts").document(doc_data["fact_id"]).set,
                    doc_data
                )

        except Exception as e:
            logger.error(f"Error storing fact: {e}")

    # 6. Check buffer size — trigger immediate flush if threshold exceeded
    if HAS_REDIS and newly_buffered > 0:
        try:
            buffer_len = redis_client.llen(f"mem_buffer:{user_id}")
            if buffer_len >= MEMORY_BUFFER_MAX:
                logger.info(f"Buffer threshold reached ({buffer_len} facts) for {user_id}. Triggering immediate flush.")
                from backend.services.orchestrator.memory_tasks import flush_memory_buffer
                flush_memory_buffer.delay(user_id)
        except Exception as e:
            logger.warning(f"Immediate flush trigger failed (non-critical): {e}")



async def search_relevant_facts(user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Perform semantic search for relevant user facts."""
    if not user_id: return []
    
    try:
        query_embedding = np.array(await asyncio.to_thread(embed_text, query))
        
        docs = firestore_db.collection("user_facts") \
            .where("user_id", "==", user_id) \
            .limit(100) \
            .stream()
        
        scored_facts = []
        for doc in docs:
            data = doc.to_dict()
            fact_text = data.get("fact")
            if fact_text is None: continue # Issue Fix: Avoid None facts

            fact_emb = np.array(data.get("embedding", []))
            if fact_emb.size > 0:
                score = cosine_sim(query_embedding, fact_emb)
                scored_facts.append({
                    "fact": fact_text,
                    "category": data.get("category"),
                    "score": score,
                    "id": doc.id
                })
        
        scored_facts.sort(key=lambda x: x["score"], reverse=True)
        return scored_facts[:limit]
    except Exception as e:
        logger.error(f"Error searching relevant facts: {e}")
        return []

async def prune_old_facts(user_id: str):
    """Prune facts older than 30 days.
    
    CRITICAL BUG FIX: We now use native datetime objects for the query.
    Firestore's '<' operator expects the same type as the field.
    """
    expiry_date = datetime.utcnow() - timedelta(days=FACT_EXPIRY_DAYS)

    try:
        old_docs = await asyncio.to_thread(
            lambda: list(
                firestore_db.collection("user_facts")
                .where("user_id", "==", user_id)
                .where("created_at", "<", expiry_date)
                .stream()
            )
        )

        count = 0
        for doc in old_docs:
            await asyncio.to_thread(doc.reference.delete)
            count += 1

        if count > 0:
            logger.info(f"Pruned {count} old facts for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to prune facts for {user_id}: {e}")
