import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

from backend.db.redis import r as redis_client, HAS_REDIS
from backend.db.postgres_db import PostgresDB
from backend.db.models import Mission, UserFact
from backend.db.neo4j_connector import Neo4jStore
from sqlalchemy import select

logger = logging.getLogger(__name__)

class ReconciliationWorker:
    """
    Sovereign v16.2: Memory Reconciliation Worker (Self-Healing).
    Ensures structural integrity across T1 (Redis), T2 (Postgres), and T4 (Neo4j).
    """
    
    def __init__(self):
        self.neo4j = Neo4jStore()

    async def run_full_reconciliation(self, user_id: str = "global"):
        """
        Structural Audit of Memory Tiers.
        Checks for orphan missions and stale relational truths.
        """
        logger.info(f"🔍 [Reconciliation] Starting full audit for: {user_id}")
        
        # 1. T1 vs T2: Active Mission Alignment
        await self._reconcile_active_missions()
        
        # 2. T2 vs T4: Relational Grounding Audit
        await self._reconcile_relational_truth(user_id)
        
        logger.info("✅ [Reconciliation] Audit complete.")

    async def _reconcile_active_missions(self):
        """Detects 'Ghost Missions' in Redis that aren't in Postgres."""
        if not HAS_REDIS: return
        
        t1_missions = redis_client.hgetall("orchestrator:missions")
        async with PostgresDB._session_factory() as session:
            for mid_bytes, data_bytes in t1_missions.items():
                mid = mid_bytes.decode()
                data = json.loads(data_bytes.decode())
                
                res = await session.execute(select(Mission).where(Mission.mission_id == mid))
                mission_db = res.scalar_one_or_none()
                
                if not mission_db and data.get("state") == "RUNNING":
                    # If it's been running for > 1 hour, it's likely a ghost
                    started_at = float(data.get("timestamp", 0))
                    if (datetime.now(timezone.utc).timestamp() - started_at) > 3600:
                        logger.warning(f"👻 [Reconciliation] Ghost Mission detected in T1: {mid}. Pruning.")
                        redis_client.hdel("orchestrator:missions", mid)
                
                elif mission_db and mission_db.status.upper() != data.get("state"):
                    # T2 (Authoritative) wins for finalized missions
                    if mission_db.status in ["completed", "failed"]:
                        logger.info(f"🔄 [Reconciliation] Finalizing T1 state for {mid} to {mission_db.status}")
                        data["state"] = mission_db.status.upper()
                        redis_client.hset("orchestrator:missions", mid, json.dumps(data))

    async def _reconcile_relational_truth(self, user_id: str):
        """Ensures facts in Postgres (T2) are mapped into Neo4j (T4)."""
        async with PostgresDB._session_factory() as session:
            stmt = select(UserFact).where(UserFact.user_id == user_id).limit(100)
            res = await session.execute(stmt)
            facts = res.scalars().all()
            
            for fact in facts:
                # Check if Neo4j has this node (simplistic check)
                # In production, we'd use a 'synced_to_graph' flag in Postgres
                exists = await self.neo4j.check_causal_bottleneck(user_id, fact.fact)
                if not exists.get("bottleneck_detected"):
                    # Sync if missing or low resonance
                    logger.info(f"🌿 [Reconciliation] Grounding T2 fact into T4: {fact.id}")
                    await self.neo4j.store_generic_fact(
                        subject=user_id,
                        relation="KNOWS_FACT",
                        obj=fact.fact[:50],
                        mission_id="reconciliation"
                    )

reconciliation_worker = ReconciliationWorker()
