"""
Sovereign Postgres SQL Fabric v14.0.0 [STABLE PROXY].
Redirects to backend.db.postgres for unified session management.
"""
from .postgres import PostgresDB as UnifiedDB, Base, postgres_db as unified_postgres_db
from contextlib import asynccontextmanager

class PostgresDB(UnifiedDB):
    """
    Sovereign Postgres Compatibility Bridge (v14.0.0).
    Maps legacy v13 PostgresDB calls to the consolidated v14 SQL Fabric.
    """
    @staticmethod
    def _session_factory():
        return UnifiedDB._session_factory_internal()

@asynccontextmanager
async def get_read_session():
    async with UnifiedDB.session_scope() as session:
        yield session

@asynccontextmanager
async def get_write_session():
    async with UnifiedDB.session_scope() as session:
        yield session

async def verify_resonance():
    return await UnifiedDB.check_health()

# Global instance for common service access
postgres_db = unified_postgres_db
