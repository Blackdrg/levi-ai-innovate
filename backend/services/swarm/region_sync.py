"""
Sovereign Regional Sync Bridge v16.1 (Task 2.5).
Handles the synchronization of critical episodic memory and mission state between regional Hive nodes.
Utilizes the DCN Raft log for strong consistency on global state.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

from backend.db.postgres import PostgresDB
from backend.db.models import Mission, UserFact
from backend.core.dcn_protocol import get_dcn_protocol
from sqlalchemy import select

logger = logging.getLogger(__name__)

class RegionSyncBridge:
    """
    Orchestrates data replication between disparate DCN regions.
    Ensures 'Follower' regions eventually reach parity with the 'Leader' region for a specific User ID.
    """
    
    def __init__(self):
        self.dcn = get_dcn_protocol()

    async def sync_user_to_hive(self, user_id: str):
        """
        Gathers recent mission criticals for a user and broadcasts a 'Replication Pulse'.
        Used when a user connects from a new region.
        """
        logger.info(f"🔄 [RegionSync] Initializing hive replication for user {user_id}")
        
        async with PostgresDB._session_factory() as session:
            # 1. Fetch recent missions
            stmt = select(Mission).where(Mission.user_id == user_id).limit(20)
            res = await session.execute(stmt)
            missions = res.scalars().all()
            
            # 2. Fetch critical facts
            stmt_f = select(UserFact).where(UserFact.user_id == user_id).where(UserFact.importance > 0.8)
            res_f = await session.execute(stmt_f)
            facts = res_f.scalars().all()

        payload = {
            "user_id": user_id,
            "missions": [{"id": m.mission_id, "objective": m.objective, "status": m.status} for m in missions],
            "facts": [{"fact": f.fact, "category": f.category} for f in facts]
        }
        
        # Broadcast via DCN Gossip (Consensus Mode: RAFT for strong sync)
        await self.dcn.broadcast_gossip(
            mission_id=f"sync_{user_id}",
            payload=payload,
            pulse_type="regional_replication_pulse"
        )
        logger.info(f"✅ [RegionSync] Replication pulse emitted for {user_id}.")

    async def handle_replication_pulse(self, payload: Dict[str, Any]):
        """Consumes a replication pulse and upserts data into the local regional DB."""
        user_id = payload.get("user_id")
        missions = payload.get("missions", [])
        facts = payload.get("facts", [])
        
        logger.info(f"📥 [RegionSync] Receiving replication data for user {user_id} ({len(missions)} missions)")
        
        async with PostgresDB._session_factory() as session:
            async with session.begin():
                # 1. Upsert Missions
                for m_data in missions:
                    # Unique identifier for Mission is mission_id
                    stmt = select(Mission).where(Mission.mission_id == m_data["id"])
                    res = await session.execute(stmt)
                    mission = res.scalar_one_or_none()
                    
                    if not mission:
                        mission = Mission(
                            mission_id=m_data["id"],
                            user_id=user_id,
                            objective=m_data["objective"],
                            status=m_data["status"]
                        )
                        session.add(mission)
                        logger.info(f"🆕 [RegionSync] New Mission added via sync: {m_data['id']}")
                    else:
                        mission.status = m_data["status"] # Consistency update
                        logger.debug(f"🔄 [RegionSync] Mission {m_data['id']} status updated to {m_data['status']}")
                
                # 2. Upsert Facts
                for f_data in facts:
                    # Uniqueness: user_id + fact content
                    stmt_f = select(UserFact).where(
                        UserFact.user_id == user_id,
                        UserFact.fact == f_data["fact"]
                    )
                    res_f = await session.execute(stmt_f)
                    fact = res_f.scalar_one_or_none()
                    
                    if not fact:
                        fact = UserFact(
                            user_id=user_id,
                            fact=f_data["fact"],
                            category=f_data.get("category", "general"),
                            importance=f_data.get("importance", 0.5)
                        )
                        session.add(fact)
                        logger.info(f"🆕 [RegionSync] New UserFact added via sync for {user_id}")
            
            await session.commit()
        
        logger.info(f"✨ [RegionSync] User {user_id} synchronized to local region.")

region_sync = RegionSyncBridge()
