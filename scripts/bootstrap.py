# scripts/bootstrap.py
import asyncio
import logging
import os
from sqlalchemy import create_engine, text
from backend.db.postgres import PostgresDB
from backend.db.redis import get_redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Bootstrap")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:sovereign_password@localhost:5432/levi_ai")

async def init_postgres():
    logger.info("🐘 Initializing Postgres Substrate (T2)...")
    try:
        # Create tables (Assumes models are imported or using raw SQL for bootstrap)
        # In a real app, we'd use Alembic. Here we ensure the DB exists.
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS system_metadata (key TEXT PRIMARY KEY, value TEXT);"))
            conn.execute(text("INSERT INTO system_metadata (key, value) VALUES ('version', '22.1') ON CONFLICT (key) DO NOTHING;"))
            conn.commit()
        logger.info("✅ Postgres initialized.")
    except Exception as e:
        logger.error(f"❌ Postgres init failed: {e}")

async def init_redis():
    logger.info("🌶️ Initializing Redis Working Memory (T1)...")
    try:
        r = get_redis_client()
        r.set("system:status", "online")
        r.set("system:boot_ts", str(asyncio.get_event_loop().time()))
        logger.info("✅ Redis initialized.")
    except Exception as e:
        logger.error(f"❌ Redis init failed: {e}")

async def main():
    logger.info("🚀 LEVI-AI: Initializing Sovereign Substrate...")
    await init_postgres()
    await init_redis()
    logger.info("🏁 Bootstrap Complete. System ready for MISSION_START.")

if __name__ == "__main__":
    asyncio.run(main())
