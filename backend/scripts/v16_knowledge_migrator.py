"""
LEVI-AI Knowledge Migration Engine v16.1.
Phase 1.10: Migration script for Tier-2 knowledge resonance.
Seeds the Neo4j Knowledge Graph from historically successful Postgres mission patterns.
"""

import asyncio
import logging
import json
import os
from typing import List, Dict, Any
from sqlalchemy import select
from datetime import datetime

from backend.db.postgres import PostgresDB
from backend.db.models import Mission
from backend.core.memory_utils import extract_memory_graph
from backend.db.neo4j_connector import Neo4jStore
from backend.utils.runtime_tasks import create_tracked_task

# Configuration
BATCH_SIZE = 50
MIN_FIDELITY = 0.85
MAX_MISSIONS = 500 # Guardrail for initial migration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrator")

class KnowledgeMigrator:
    def __init__(self):
        self.neo4j = Neo4jStore()

    async def run(self):
        logger.info("🚀 [Migrator] Starting Knowledge Resonance Migration (SQL -> Graph)...")
        
        # 1. Fetch successful missions
        async with PostgresDB._session_factory() as session:
            stmt = (
                select(Mission)
                .where(Mission.status == "completed")
                .where(Mission.fidelity_score >= MIN_FIDELITY)
                .order_by(Mission.updated_at.desc())
                .limit(MAX_MISSIONS)
            )
            result = await session.execute(stmt)
            missions = result.scalars().all()
        
        if not missions:
            logger.info("ℹ️ [Migrator] No eligible missions found for migration.")
            return

        logger.info(f"📦 [Migrator] Found {len(missions)} mission candidates.")
        
        # 2. Process in batches to avoid rate limiting or memory bloat
        for i in range(0, len(missions), BATCH_SIZE):
            batch = missions[i:i + BATCH_SIZE]
            logger.info(f"🔨 [Migrator] Processing batch {i//BATCH_SIZE + 1}...")
            
            tasks = [self._migrate_single_mission(m) for m in batch]
            await asyncio.gather(*tasks)
            
        logger.info("✅ [Migrator] Graduation Complete. Knowledge Resonance synchronized.")

    async def _migrate_single_mission(self, mission: Mission):
        """Extracts and upserts triplets for a single mission."""
        try:
            # Reconstruct the interaction summary
            # We assume bot output is stored in mission.payload or similar
            response = str(mission.payload.get("output", "")) if isinstance(mission.payload, dict) else ""
            
            # 1. Extract Triplets from historical data
            extraction = await extract_memory_graph(
                user_input=mission.objective,
                bot_response=response,
                agent_traces="Historical Mission Trace"
            )
            
            triplets = extraction.get("triplets", [])
            if not triplets:
                return

            # 2. Upsert to Neo4j
            for t in triplets:
                await self.neo4j.store_generic_fact(
                    subject=t["subject"],
                    relation=t["relation"],
                    obj=t["object"],
                    tenant_id="default",
                    mission_id=mission.mission_id
                )
            
            logger.info(f"✨ [Migrator] Migrated {len(triplets)} triplets for mission {mission.mission_id}")
            
        except Exception as e:
            logger.error(f"❌ [Migrator] Failed to migrate mission {mission.mission_id}: {e}")

async def main():
    migrator = KnowledgeMigrator()
    await migrator.run()

if __name__ == "__main__":
    asyncio.run(main())
