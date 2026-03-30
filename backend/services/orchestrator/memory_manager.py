import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.redis_client import get_conversation, save_conversation
from backend.firestore_db import db as firestore_db

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages 3 layers of memory with Phase 2 Soul Upgrades."""

    @staticmethod
    def get_short_term_memory(session_id: str) -> List[Dict[str, Any]]:
        """Instant session awareness from Redis."""
        return get_conversation(session_id)

    @staticmethod
    def get_mid_term_memory(user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Recent interaction history (Pulse) from Firestore."""
        if not user_id: return []
        
        try:
            docs = firestore_db.collection("conversations") \
                .where("user_id", "==", user_id) \
                .order_by("updated_at", direction="DESCENDING") \
                .limit(limit) \
                .stream()
            
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error fetching mid-term memory: {e}")
            return []

    @staticmethod
    async def get_long_term_memory(user_id: str, query: str = "") -> Dict[str, Any]:
        """Retrieve categorized facts and user traits."""
        if not user_id: return {}
        
        try:
            from .memory_utils import search_relevant_facts, prune_old_facts
            
            # 1. Trigger 30-day pruning (Maintenance)
            await prune_old_facts(user_id)
            
            # 2. Semantic Search for specialized context
            relevant_facts = await search_relevant_facts(user_id, query, limit=10)
            
            # 3. Categorize facts for the synthesizer
            categorized = {
                "preferences": [f["fact"] for f in relevant_facts if f["category"] == "preference"],
                "traits": [f["fact"] for f in relevant_facts if f["category"] == "trait"],
                "history": [f["fact"] for f in relevant_facts if f["category"] == "history"],
                "other": [f["fact"] for f in relevant_facts if f["category"] == "factual"]
            }
            
            return categorized
        except Exception as e:
            logger.error(f"Error fetching long-term memory: {e}")
            return {}

    @staticmethod
    def store_memory(user_id: str, session_id: str, user_input: str, bot_response: str):
        """Update Redis (Short-term) and Firestore interaction logs."""
        history = get_conversation(session_id)
        history.append({
            "user": user_input,
            "bot": bot_response,
            "timestamp": datetime.utcnow().isoformat()
        })
        save_conversation(session_id, history, user_id=user_id)

    @staticmethod
    async def process_new_interaction(user_id: str, user_input: str, bot_response: str):
        """Phase 2 Background Task: Fact Extraction, Deduplication, and Pulse Update."""
        from .memory_utils import extract_facts, store_facts
        try:
            # 1. Extract categorized facts
            new_facts = await extract_facts(user_input, bot_response)
            
            # 2. Store with semantic deduplication
            if new_facts:
                await store_facts(user_id, new_facts)
                
            # 3. Update User Interaction Pulse (Mood tracking)
            # This is handled by updating the user profile or a specific pulse collection
            # For now, we rely on Mid-term memory queries.
            
        except Exception as e:
            logger.error(f"Failed to process interaction for memory: {e}")

    @staticmethod
    async def get_combined_context(user_id: str, session_id: str, query: str = "") -> Dict[str, Any]:
        """Combine all 3 layers into a rich context object for the Brain."""
        import asyncio
        
        # Parallelize memory retrieval for lower latency
        short_term_task = asyncio.to_thread(MemoryManager.get_short_term_memory, session_id)
        mid_term_task = asyncio.to_thread(MemoryManager.get_mid_term_memory, user_id, 3)
        long_term_task = MemoryManager.get_long_term_memory(user_id, query)
        
        short_term, mid_term, long_term = await asyncio.gather(
            short_term_task, mid_term_task, long_term_task
        )
        
        # Calculate 'Interaction Pulse' (Recent Mood)
        moods = [m.get("mood", "philosophical") for m in mid_term if m.get("mood")]
        pulse = moods[0] if moods else "stable"
        
        # Determine Feature Flags based on tier (Phase 5)
        from backend.config import TIERS # type: ignore
        # Here we'd typically have the user object, but for now we pass flags
        
        return {
            "history": short_term,
            "long_term": long_term,
            "mid_term": mid_term, # Include mid-term for deeper pulse analysis
            "interaction_pulse": pulse,
            "user_id": user_id,
            "session_id": session_id
        }
