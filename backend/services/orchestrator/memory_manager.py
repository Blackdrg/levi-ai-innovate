import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.redis_client import get_conversation, save_conversation
from backend.firestore_db import db as firestore_db

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages 3 layers of memory: Short-Term, Mid-Term, and Long-Term."""

    @staticmethod
    def get_short_term_memory(session_id: str) -> List[Dict[str, Any]]:
        """Get the current conversation history from Redis/Firestore."""
        return get_conversation(session_id)

    @staticmethod
    def get_mid_term_memory(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the recent interaction history for a user across multiple sessions."""
        if not user_id: return []
        
        try:
            # Query the sessions associated with the user and get combined history
            docs = firestore_db.collection("conversations") \
                .where("user_id", "==", user_id) \
                .order_by("updated_at", direction="DESCENDING") \
                .limit(limit) \
                .stream()
            
            combined_history = []
            for doc in docs:
                combined_history.extend(doc.to_dict().get("history", []))
            
            return combined_history[:limit]
        except Exception as e:
            logger.error(f"Error fetching mid-term memory: {e}")
            return []

    @staticmethod
    async def get_long_term_memory(user_id: str, query: str = "") -> Dict[str, Any]:
        """Get semantic facts and preferences about the user."""
        if not user_id: return {}
        
        try:
            # 1. Base Preferences from Profile
            profile = {}
            doc = firestore_db.collection("user_profiles").document(user_id).get()
            if doc.exists:
                profile = doc.to_dict().get("preferences", {})
            
            # 2. Semantic Search for Relevant Facts (LTM Upgrade)
            from .memory_utils import search_relevant_facts
            facts = await search_relevant_facts(user_id, query)
            
            return {
                "profile": profile,
                "relevant_facts": facts
            }
        except Exception as e:
            logger.error(f"Error fetching long-term memory: {e}")
            return {}

    @staticmethod
    def store_memory(user_id: str, session_id: str, user_input: str, bot_response: str):
        """Update historical layers with new interaction."""
        history = get_conversation(session_id)
        history.append({
            "user": user_input,
            "bot": bot_response,
            "timestamp": datetime.utcnow().isoformat()
        })
        save_conversation(session_id, history, user_id=user_id)

    @staticmethod
    async def process_new_interaction(user_id: str, user_input: str, bot_response: str):
        """Background task to extract and store facts from interaction."""
        from .memory_utils import extract_facts, store_facts
        try:
            facts = await extract_facts(user_input, bot_response)
            if facts:
                await store_facts(user_id, facts)
        except Exception as e:
            logger.error(f"Failed to process interaction for memory: {e}")

    @staticmethod
    async def get_combined_context(user_id: str, session_id: str, query: str = "") -> Dict[str, Any]:
        """Retrieve and combine memory layers for the current prompt."""
        short_term = MemoryManager.get_short_term_memory(session_id)
        
        # Mid/Long term fetches
        long_term = await MemoryManager.get_long_term_memory(user_id, query)
        
        return {
            "history": short_term,
            "long_term": long_term, # Contains profile and relevant_facts
            "current_session": session_id,
            "user_id": user_id
        }
