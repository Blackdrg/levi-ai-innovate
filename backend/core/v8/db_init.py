import asyncio
import os
import logging
import asyncpg
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def initialize_v8_persistence():
    """
    LeviBrain v8: Persistence Layer Initializer.
    Migrates the 'Sovereign OS Fabric' schema to the production Postgres instance.
    """
    database_url = os.getenv("DATABASE_URL", "postgresql://levi:levi_pass@localhost:5432/levidb")
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    
    if not os.path.exists(schema_path):
        logger.error(f"[V8 DB-Init] Schema file not found at {schema_path}")
        return

    try:
        logger.info(f"[V8 DB-Init] Connecting to Sovereign Postgres at {database_url.split('@')[1]}...")
        conn = await asyncpg.connect(database_url)
        
        with open(schema_path, "r") as f:
            schema_sql = f.read()

        logger.info("[V8 DB-Init] Executing v8 high-fidelity migration...")
        await conn.execute(schema_sql)
        
        logger.info("[V8 DB-Init] Graduation complete. Multi-store persistence layer is now active.")
        await conn.close()
        
    except Exception as e:
        logger.error(f"[V8 DB-Init] Migration failure: {e}")

if __name__ == "__main__":
    asyncio.run(initialize_v8_persistence())
