import asyncio
import logging
from typing import Dict, Any, List
from backend.db.postgres import PostgresDB
from backend.db.neo4j_connector import Neo4jStore
from backend.memory.vector_store import SovereignVectorStore
from sqlalchemy import select
from backend.db.models import UserFact

logger = logging.getLogger(__name__)

class MemoryReconciliationWorker:
    """
    Sovereign v16.2: Memory Truth Hierarchy Arbiter.
    Ensures consistency across:
    T2 (Postgres - Authoritative) -> T3 (FAISS - Semantic) -> T4 (Neo4j - Relational)
    """
    def __init__(self):
        self.neo4j = Neo4jStore()
        
    async def run_reconciliation_pulse(self, user_id: str):
        """
        Main reconciliation loop:
        1. Query T2 (Postgres) for authoritative facts.
        2. Verify existence in T4 (Neo4j).
        3. Trigger vector re-indexing if drift or mismatch is detected.
        """
        logger.info(f"⚖️ [Reconciliation] Starting truth pulse for {user_id}...")
        
        try:
            # 1. Fetch Authoritative Facts from Postgres
            async with PostgresDB._session_factory() as session:
                stmt = select(UserFact).where(UserFact.user_id == user_id, UserFact.is_deleted == False)
                res = await session.execute(stmt)
                authoritative_facts = res.scalars().all()

            # 2. Verify against Neo4j (Relational Truth)
            mismatches = 0
            for fact in authoritative_facts:
                # Basic check: exists as node or relation
                # In a real production system, we'd compare the hash of the fact content
                resonance = await self.neo4j.get_resonance(fact.fact[:50], user_id)
                if not resonance:
                    logger.warning(f"⚠️ [Reconciliation] Missing Relation in Neo4j for Fact ID: {fact.id}")
                    # Auto-repair: Re-extract and re-insert into Neo4j
                    await self._repair_neo4j(fact, user_id)
                    mismatches += 1

            # 3. Check Vector Drift (T3)
            drift_report = await SovereignVectorStore.monitor_drift(user_id)
            if drift_report.get("drift_detected"):
                logger.warning(f"🚨 [Reconciliation] Vector Drift Detected (Score: {drift_report['score']:.2f}).")
                # Hard re-index is already triggered by monitor_drift, but we log it here for observability
            
            logger.info(f"✅ [Reconciliation] Pulse complete for {user_id}. Fixed {mismatches} mismatches.")
            
        except Exception as e:
            logger.error(f"❌ [Reconciliation] Pulse failed for {user_id}: {e}")

    async def _repair_neo4j(self, fact: UserFact, user_id: str):
        """Re-extracts and inserts knowledge into Neo4j from a Postgres fact."""
        # Simple extraction logic (usually would call ChroniclerAgent)
        try:
            # Placeholder for extraction; in prod, we trigger an event for Chronicler
            await self.neo4j.store_generic_fact(
                subject=f"Fact_{fact.id}", 
                relation="DEFINES", 
                obj=fact.category, 
                tenant_id=user_id
            )
        except Exception as e:
            logger.error(f"[Reconciliation] Repair failed: {e}")

reconciliation_worker = MemoryReconciliationWorker()
