"""
Sovereign Dreaming Task v8.
Automates the cognitive transition from episodic fragments to crystallized semantic traits.
Triggered by mission completion or periodic intervals.
"""
import asyncio
import logging
from backend.services.learning.distiller import MemoryDistiller
from backend.redis_client import SovereignCache

logger = logging.getLogger(__name__)

class DreamingTask:
    """
    Orchestrates the 'Dreaming Phase' across the Sovereign OS.
    Tracks mission count in Redis to trigger distillation.
    """
    
    MISSION_THRESHOLD = 5 # Trigger dreaming every 5 missions
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
            
            distiller = MemoryDistiller()
            # Run distillation in the background to not block the current mission response
            asyncio.create_task(distiller.distill_user_memory(user_id))
            return True
            
        return False

    @classmethod
    async def trigger_force(cls, user_id: str):
        """Manually force a dreaming phase."""
        distiller = MemoryDistiller()
        await distiller.distill_user_memory(user_id)
