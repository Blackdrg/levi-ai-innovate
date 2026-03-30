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

async def store_facts(user_id: str, new_facts: List[Dict[str, Any]]):
    """Embed and store facts with semantic deduplication."""
    if not user_id or not new_facts: return
    
    # 1. Fetch existing facts to perform deduplication
    existing_docs = firestore_db.collection("user_facts") \
        .where("user_id", "==", user_id) \
        .stream()
    
    existing_facts = []
    for doc in existing_docs:
        existing_facts.append(doc.to_dict())

    for item in new_facts:
        fact_text = item.get("fact")
        category = item.get("category", "factual")
        if not fact_text: continue
        
        try:
            new_embedding = await asyncio.to_thread(embed_text, fact_text)
            
            # 2. Deduplication check
            is_duplicate = False
            for old_fact in existing_facts:
                old_emb = np.array(old_fact.get("embedding", []))
                if old_emb.size > 0:
                    similarity = cosine_sim(np.array(new_embedding), old_emb)
                    if similarity > FACT_DEDUPLICATION_THRESHOLD:
                        logger.info(f"Deduplicated fact: '{fact_text}' matches existing '{old_fact.get('fact')}'")
                        is_duplicate = True
                        break
            
            if is_duplicate: continue

            # 3. Store new unique fact - Non-blocking I/O
            fact_id = hashlib.md5(fact_text.encode()).hexdigest()
            doc_data = {
                "user_id": user_id,
                "fact": fact_text,
                "category": category,
                "embedding": new_embedding,
                "created_at": datetime.utcnow()
            }
            
            await asyncio.to_thread(
                firestore_db.collection("user_facts").document(f"{user_id}_{fact_id}").set,
                doc_data
            )
        except Exception as e:
            logger.error(f"Error storing fact: {e}")

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
    """Prune facts older than 30 days as requested."""
    expiry_date = datetime.utcnow() - timedelta(days=FACT_EXPIRY_DAYS)
    
    try:
        old_docs = firestore_db.collection("user_facts") \
            .where("user_id", "==", user_id) \
            .where("created_at", "<", expiry_date) \
            .stream()
            
        count = 0
        for doc in old_docs:
            doc.reference.delete()
            count += 1
        
        if count > 0:
            logger.info(f"Pruned {count} old facts for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to prune facts for {user_id}: {e}")
