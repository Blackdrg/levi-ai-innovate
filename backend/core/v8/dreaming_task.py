"""
Sovereign Dreaming Task v8.
Automates the cognitive transition from episodic fragments to crystallized semantic traits.
Triggered by mission completion or periodic intervals.
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from backend.services.learning.distiller import MemoryDistiller
from backend.redis_client import SovereignCache

logger = logging.getLogger(__name__)

class DreamingTask:
    """
    Orchestrates the 'Dreaming Phase' across the Sovereign OS.
    Tracks mission count in Redis to trigger distillation.
    """
    
    MISSION_THRESHOLD = 10 # Phase 4: 10 interactions -> 1 insight
    MISSION_COUNTER_KEY = "sovereign:internal:mission_count"

    @classmethod
    async def increment_and_check(cls, user_id: str):
        """Called after a mission is completed."""
        client = SovereignCache.get_client()
        key = f"{cls.MISSION_COUNTER_KEY}:{user_id}"
        
        count = client.incr(key)
        logger.debug(f"[DreamingTask] Mission count for {user_id}: {count}")
        
        if count >= cls.MISSION_THRESHOLD:
            logger.info(f"[DreamingTask] Threshold reached ({count}). Initiating Dreaming Phase for {user_id}...")
            client.set(key, 0) # Reset
            
            # v11.0: Run insight compression and distillation
            from backend.utils.runtime_tasks import create_tracked_task
            create_tracked_task(cls.calculate_insight(user_id), name=f"dream-insight-{user_id}")
            
            distiller = MemoryDistiller()
            from backend.utils.runtime_tasks import create_tracked_task
            create_tracked_task(distiller.distill_user_memory(user_id), name=f"dream-distill-{user_id}")
            return True
            
        return False

    @classmethod
    async def calculate_insight(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Phase 4: Interaction-to-Insight Compression.
        Converts 10 recent interactions into 1 behavioral insight.
        """
        from backend.core.memory_manager import MemoryManager
        from backend.core.planner import call_lightweight_llm
        import json
        
        memory = MemoryManager()
        history = await memory.get_mid_term(user_id, limit=10)
        if len(history) < 5: return None
        
        interactions = []
        for m in history:
             # Handle list of dicts from Firestore conversations
             interactions.append(f"User: {m.get('user_input', '')}\nAI: {m.get('response', '')}")
        
        history_text = "\n---\n".join(interactions)
        
        prompt = (
            "Analyze the following interactions. Extract ONE deep behavioral insight about the user pattern.\n"
            "Focus on behavior, preferences, or style.\n"
            f"Interactions:\n{history_text}\n\n"
            "Output ONLY JSON: {\"behavior_pattern\": \"...\", \"confidence\": 0.9, \"insight\": \"...\"}"
        )
        
        try:
            raw_json = await call_lightweight_llm([{"role": "system", "content": prompt}])
            if "```json" in raw_json: raw_json = raw_json.split("```json")[1].split("```")[0]
            insight_data = json.loads(raw_json.strip())
            
            # Store in Identity Layer (T4)
            from backend.memory.vector_store import SovereignVectorStore
            await SovereignVectorStore.store_fact(
                user_id, 
                f"Identity Insight: {insight_data['insight']}", 
                category="insight", 
                importance=insight_data.get("confidence", 0.8)
            )
            logger.info(f"[DreamingTask] Phase 4 Insight Generated for {user_id}: {insight_data['insight']}")
            return insight_data
        except Exception as e:
            logger.error(f"[DreamingTask] Insight compression failed: {e}")
            return None

    @classmethod
    async def trigger_force(cls, user_id: str):
        """Manually force a dreaming phase."""
        distiller = MemoryDistiller()
        await distiller.distill_user_memory(user_id)
