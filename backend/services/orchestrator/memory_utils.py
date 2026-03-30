import json
import logging
from typing import List, Dict, Any, Optional
from backend.embeddings import embed_text, cosine_sim
from backend.firestore_db import db as firestore_db
import numpy as np

logger = logging.getLogger(__name__)

async def extract_facts(user_input: str, bot_response: str) -> List[str]:
    """Uses LLM to extract atomic facts about the user from the interaction."""
    from backend.services.orchestrator.planner import call_lightweight_llm
    
    system_prompt = (
        "You are the LEVI Memory Extractor. Extract key, atomic facts about the user "
        "from the conversation. For example: 'User likes philosophical discussion', "
        "'User is interested in stoicism'. Output a JSON array of strings. "
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

async def store_facts(user_id: str, facts: List[str]):
    """Embed and store facts in Firestore."""
    if not user_id or not facts: return
    
    for fact in facts:
        try:
            embedding = embed_text(fact)
            fact_id = hashlib.md5(fact.encode()).hexdigest()
            
            firestore_db.collection("user_facts").document(f"{user_id}_{fact_id}").set({
                "user_id": user_id,
                "fact": fact,
                "embedding": embedding,
                "created_at": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Error storing fact: {e}")

async def search_relevant_facts(user_id: str, query: str, limit: int = 5) -> List[str]:
    """Perform semantic search for relevant user facts."""
    if not user_id: return []
    
    try:
        query_embedding = np.array(embed_text(query))
        
        # Note: For large datasets, use a vector DB. For Firestore, we fetch a subset and rank.
        docs = firestore_db.collection("user_facts") \
            .where("user_id", "==", user_id) \
            .limit(100) \
            .stream()
        
        scored_facts = []
        for doc in docs:
            data = doc.to_dict()
            fact_emb = np.array(data.get("embedding", []))
            if fact_emb.size > 0:
                score = cosine_sim(query_embedding, fact_emb)
                scored_facts.append((data.get("fact"), score))
        
        scored_facts.sort(key=lambda x: x[1], reverse=True)
        return [f[0] for f in scored_facts[:limit]]
    except Exception as e:
        logger.error(f"Error searching relevant facts: {e}")
        return []

import hashlib
from datetime import datetime
