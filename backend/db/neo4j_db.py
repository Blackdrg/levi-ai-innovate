import os
import logging
from neo4j import GraphDatabase, AsyncGraphDatabase
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "levi_pass_graph")

class SovereignGraph:
    """
    Sovereign Knowledge Graph v8 Connection Manager.
    Handles high-concurrency Bolt connections to the Neo4j cluster.
    """
    _driver = None
    _async_driver = None

    @classmethod
    def get_driver(cls):
        if cls._driver is None:
            try:
                cls._driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
                cls._driver.verify_connectivity()
                logger.debug(f"[GraphDB] Neo4j Sync Driver Initialized at {NEO4J_URI}")
            except Exception as e:
                logger.error(f"[GraphDB] Sync Connectivity failure: {e}")
        return cls._driver

    @classmethod
    async def get_async_driver(cls):
        if cls._async_driver is None:
            try:
                driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
                await driver.verify_connectivity()
                cls._async_driver = driver
                logger.info(f"[GraphDB] Neo4j Async Driver Initialized at {NEO4J_URI}")
            except Exception as e:
                logger.error(f"[GraphDB] Async Connectivity failure: {e}")
                return None
        return cls._async_driver

    @classmethod
    async def close(cls):
        if cls._driver:
            cls._driver.close()
        if cls._async_driver:
            await cls._async_driver.close()
        logger.info("[GraphDB] Neo4j connections closed.")

async def execute_query(query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Execute a Cypher query asynchronously and return results."""
    driver = await SovereignGraph.get_async_driver()
    if not driver:
        return []
    
    try:
        async with driver.session() as session:
            result = await session.run(query, parameters or {})
            records = [dict(record) for record in await result.list()]
            return records
    except Exception as e:
        logger.error(f"[GraphDB] Query execution error: {e}\nQuery: {query}")
        return []
