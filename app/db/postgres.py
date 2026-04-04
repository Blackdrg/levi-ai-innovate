import asyncpg
import os

_pg_pool = None

async def get_db_pool():
    global _pg_pool
    if not _pg_pool:
        _pg_pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
    return _pg_pool
