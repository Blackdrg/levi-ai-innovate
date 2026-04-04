import logging
import asyncio
from datetime import datetime, timedelta, timezone
from backend.utils.vector_db import VectorDB

logger = logging.getLogger(__name__)

class SurvivalGater:
    """
    Sovereign v9.8.1: Memory Hygiene Service.
    Purges low-fidelity and expired memories from the vector store to maintain cognitive health.
    """

    @staticmethod
    async def purge_low_fidelity_memories(user_id: str = None, collection: str = "memory"):
        """
        Scans specified collection for memories with Survival Score < 0.5 or Age > 90 days.
        """
        logger.info(f"[Hygiene] Initiating Survival Audit: {user_id or 'global'}/{collection}")
        
        try:
            if user_id:
                db = await VectorDB.get_user_collection(user_id, collection)
            else:
                db = await VectorDB.get_collection(collection)
        except Exception as e:
            logger.error(f"[Hygiene] Failed to connect to collection: {e}")
            return 0
            
        indices_to_purge = []
        now = datetime.now(timezone.utc)
        
        # Safely iterate through metadata
        metadata = db.metadata
        
        for i, meta in enumerate(metadata):
            if meta.get("deleted"):
                continue
            
            # 1. Fidelity Gating (Score < 0.5 represents low resonance)
            survival_score = meta.get("survival_score", 1.0)
            
            # 2. Expiration Gating (90 days graduation limit)
            created_at = meta.get("created_at")
            if isinstance(created_at, str):
                try:
                    # Handle both ISO and custom formats
                    created_at_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if created_at_dt.tzinfo is None:
                        created_at_dt = created_at_dt.replace(tzinfo=timezone.utc)
                except:
                    created_at_dt = now
            elif isinstance(created_at, datetime):
                created_at_dt = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
            else:
                # Default to now if missing
                created_at_dt = now
                
            age_days = (now - created_at_dt).days
            
            # Purge if resonance is low OR memory has exceeded the 90-day sovereign window
            if survival_score < 0.5 or age_days > 90:
                indices_to_purge.append(i)
                
        if indices_to_purge:
            await db.remove_indices(indices_to_purge)
            logger.info(f"[Hygiene] MISSION_COMPLETE: {len(indices_to_purge)} records purged in '{collection}'.")
        else:
            logger.info(f"[Hygiene] MISSION_AUDIT_PASS: Zero violations in '{collection}'.")

        return len(indices_to_purge)
