import logging
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from backend.db.postgres import PostgresDB
from backend.db.redis import get_redis_client

logger = logging.getLogger(__name__)

class RetentionManager:
    """
    Sovereign Data Retention v22.1.
    Enforces 90-day archiving and storage optimization.
    """
    
    @classmethod
    async def run_archiving_cycle(cls):
        """
        Main archival cycle:
        1. Move 90-day-old missions to history table or mark for cold storage.
        2. Prune old Neo4j relationships.
        3. Audit Redis TTLs.
        """
        logger.info("📅 [Retention] Starting data retention cycle...")
        try:
            await cls.archive_postgres_missions(days=90)
            await cls.prune_neo4j_graph(days=120)
            await cls.audit_redis_ttl()
            logger.info("✅ [Retention] Cycle complete.")
        except Exception as e:
            logger.error(f"❌ [Retention] Cycle failed: {e}")

    @classmethod
    async def archive_postgres_missions(cls, days: int = 90):
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        logger.info(f"📦 [Postgres] Archiving missions older than {days} days (cutoff: {cutoff})")
        
        async with PostgresDB.session_scope() as session:
            # Sovereign v22.1: We move to 'missions_history' instead of deleting
            # First ensure missions_history exists (this would normally be a migration)
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS missions_history (LIKE missions INCLUDING ALL);
            """))
            
            # Archive operation
            insert_query = text("""
                INSERT INTO missions_history 
                SELECT * FROM missions 
                WHERE created_at < :cutoff;
            """)
            delete_query = text("""
                DELETE FROM missions 
                WHERE created_at < :cutoff;
            """)
            
            res_move = await session.execute(insert_query, {"cutoff": cutoff})
            res_del = await session.execute(delete_query, {"cutoff": cutoff})
            logger.info(f"✅ [Postgres] Archived {res_move.rowcount} missions.")

    @classmethod
    async def prune_neo4j_graph(cls, days: int = 120):
        from backend.db.neo4j_client import Neo4jClient
        logger.info(f"🕸️ [Neo4j] Pruning relationships older than {days} days.")
        
        # Section 5: Real relationship pruning
        # We prune 'EXECUTED' relationships for missions older than the cutoff
        cypher = """
        MATCH (u:User)-[r:EXECUTED]->(m:Mission)
        WHERE m.timestamp < datetime() - duration({days: $days})
        DELETE r
        """
        try:
            await Neo4jClient.execute_query(cypher, {"days": days})
            # Also prune orphan mission nodes
            await Neo4jClient.execute_query("""
                MATCH (m:Mission) 
                WHERE m.timestamp < datetime() - duration({days: $days}) 
                AND NOT (m)--()
                DELETE m
            """, {"days": days})
            logger.info("✅ [Neo4j] Relationship pruning successful.")
        except Exception as e:
            logger.error(f"❌ [Neo4j] Pruning failed: {e}")

    @classmethod
    async def audit_redis_ttl(cls):
        # Ensure all mission: keys have a TTL (e.g. 7 days for ephemeral state)
        r = get_redis_client()
        if not r: return
        logger.info("🧠 [Redis] Auditing ephemeral state TTLs.")
        
        # Scan for keys without TTL (highly simplified for this baseline)
        patterns = ["mission:*", "state:*", "cache:*"]
        count = 0
        for pattern in patterns:
            for key in r.scan_iter(pattern):
                if r.ttl(key) == -1: # No TTL
                    r.expire(key, 604800) # Force 7-day TTL
                    count += 1
        logger.info(f"✅ [Redis] TTL audit complete. Fixed {count} keys.")

    @classmethod
    async def run_graduation_cycle(cls):
        """
        Sovereign v22.1: Graduation Logic (Tier 2 -> Tier 3).
        Promotes facts with fidelity > 0.92 to permanent storage.
        """
        logger.info("🎓 [Retention] Initiating high-fidelity graduation cycle...")
        try:
            from backend.services.mcm import mcm_service
            from backend.db.models import UserFact
            async with PostgresDB.session_scope() as session:
                from sqlalchemy import select
                stmt = select(UserFact).where(UserFact.importance >= 0.92, UserFact.is_deleted == False)
                res = await session.execute(stmt)
                facts = res.scalars().all()
                
                for fact in facts:
                    # Mocking a BFT pulse for each high-fidelity fact
                    pulse = {
                        "fact_id": str(fact.id),
                        "fidelity": fact.importance,
                        "agent_id": "graduation_engine_v22"
                    }
                    await mcm_service.graduate(pulse)
            logger.info(f"✅ [Retention] Graduation cycle complete. Processed {len(facts)} candidates.")
        except Exception as e:
            logger.error(f"❌ [Retention] Graduation failed: {e}")

# Global instance
retention_manager = RetentionManager()
