import asyncio
import logging
from backend.db.postgres import PostgresDB, Base
from backend.db.models import BenchmarkLedger # Ensure it's imported for metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_init")

async def init_db():
    """
    Initializes the BenchmarkLedger table in Postgres.
    """
    logger.info("🛡️ Initiating Benchmark Database Sync...")
    engine = PostgresDB.get_engine()
    
    if not engine:
        logger.error("❌ Failed to connect to Postgres. Check DATABASE_URL.")
        return

    try:
        async with engine.begin() as conn:
            # We only create tables that don't exist
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Benchmark table synchronized successfully.")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
    finally:
        await PostgresDB.close()

if __name__ == "__main__":
    asyncio.run(init_db())
