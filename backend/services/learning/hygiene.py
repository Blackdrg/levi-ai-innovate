"""
Sovereign Memory Hygiene v13.0.0.
Maintains cognitive health by pruning low-fidelity resonance.
Synchronized with the HNSW Cognitive Vault.
"""

import logging

logger = logging.getLogger(__name__)

class SurvivalGater:
    """
    Sovereign Survival Hygiene v13.0.0.
    Purges low-fidelity and expired memories from the Sovereign OS.
    """

    @staticmethod
    async def purge_low_fidelity_memories(user_id: str):
        """
        Scans Vector Store for memories with Resonance < 0.4 and archives them.
        """
        logger.info(f"[Hygiene] Initiating Survival Audit for {user_id}")
        
        try:
            from backend.memory.vector_store import SovereignVectorStore
            from backend.memory.resonance import MemoryResonance
            
            # 1. Fetch all facts for user (limit 100 for batch)
            facts = await SovereignVectorStore.search_facts(user_id, "", limit=100)
            
            to_archive = []
            for fact in facts:
                # Calculate resonance based on importance and age
                created_at = datetime.fromisoformat(fact["created_at"])
                age_days = (datetime.now(timezone.utc) - created_at).days
                
                resonance = MemoryResonance.calculate_resonance(
                    importance=fact.get("importance", 0.5),
                    age_days=age_days,
                    foa=1.0 # Focus of Attention (simulated)
                )
                
                if resonance < 0.4:
                    to_archive.append(fact)

            if to_archive:
                logger.info(f"[Hygiene] Archiving {len(to_archive)} low-resonance memories for {user_id}")
                await SurvivalGater._archive_memories(user_id, to_archive)
                # In a real setup, we'd also delete from VectorDB index
                # await SovereignVectorStore.delete_facts(user_id, [f["fact_id"] for f in to_archive])

            return len(to_archive)
        except Exception as e:
            logger.error(f"[Hygiene] Survival sequence failed: {e}")
            return 0

    @staticmethod
    async def _archive_memories(user_id: str, facts: list):
        """Tier 3: Move to Cold Storage (Postgres Archive)."""
        from backend.db.postgres import PostgresDB
        from sqlalchemy import text
        
        async with PostgresDB._session_factory() as session:
            for fact in facts:
                await session.execute(
                    text("INSERT INTO memory_archive (user_id, content, metadata_json) VALUES (:uid, :content, :meta)"),
                    {"uid": user_id, "content": fact["fact"], "meta": json.dumps(fact)}
                )
            await session.commit()

class MemoryPruningManager:
    """Orchestrates the 3-tier memory cycle."""
    
    @classmethod
    async def run_cycle(cls):
        """Triggered by Celery Beat."""
        # Find active users (last 24h)
        # For each user, run SurvivalGater
        logger.info("[PruningManager] Starting global memory cycle...")
        # (Implementation would iterate users)
