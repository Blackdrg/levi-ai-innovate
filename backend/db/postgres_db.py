"""
Sovereign Postgres SQL Fabric v14.0.0 [STABLE PROXY].
Redirects to backend.db.postgres for unified session management.
"""

import logging
from .postgres import PostgresDB as UnifiedDB, Base
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

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
    try:
        session = await UnifiedDB.get_session_with_retry(retries=1)
        await session.close()
        return True
    except:
        return False
