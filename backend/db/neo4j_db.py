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

async def project_to_neo4j(node_result: Dict[str, Any], sync: bool = True, timeout: float = 2.0):
    """
    Sovereign v15.0: Cognitive Knowledge Projection.
    Updates the Neo4j Knowledge Graph with node execution outcomes.
    """
    query = """
    MERGE (node:MissionNode {id: $id})
    SET node.status = $status, 
        node.timestamp = $timestamp,
        node.agent = $agent,
        node.fidelity = $fidelity
    RETURN node
    """
    
    params = {
        "id": node_result.get('id', node_result.get('node_id')),
        "status": "COMPLETED" if node_result.get('success') else "FAILED",
        "timestamp": time.time(),
        "agent": node_result.get('agent', 'unknown'),
        "fidelity": node_result.get('fidelity_score', 0.0)
    }

    try:
        if sync:
            # Synchronous verification (blocks until graph confirms)
            await asyncio.wait_for(execute_query(query, params), timeout=timeout)
            logger.debug(f"[Neo4j] SYNC: Projected node {params['id']} successfully.")
            return {"status": "synced"}
        else:
            # Asynchronous background projection
            asyncio.create_task(execute_query(query, params))
            logger.debug(f"[Neo4j] ASYNC: Queued projection for node {params['id']}.")
            return {"status": "queued"}
    except asyncio.TimeoutError:
        logger.warning(f"[Neo4j] Sync timeout for node {params['id']}. Fallback to async.")
        return {"status": "timeout_fallback"}
    except Exception as e:
        logger.error(f"[Neo4j] Projection failure for {params['id']}: {e}")
        return {"status": "error", "error": str(e)}

async def get_resonance_entities(user_id: str, query_text: str) -> List[Dict[str, Any]]:
    """
    Retrieves entities and interactions related to the current query context.
    v15.0: Hardened resonance with phrase expansion and multi-hop awareness.
    """
    if not query_text: return []
    
    stop_words = {"what", "how", "show", "give", "find", "this", "that", "user"}
    terms = [t.lower() for t in query_text.replace("?", "").split() if len(t) > 3 and t.lower() not in stop_words]
    
    if not terms: return []

    cypher = """
    MATCH (u:User {id: $user_id})-[:PERFORMED|KNOWS|PREFERS]->(n)
    WHERE any(term IN $terms WHERE n.text CONTAINS term OR n.name CONTAINS term OR n.intent CONTAINS term)
    RETURN n as entity, labels(n) as labels, 
           (CASE WHEN n.importance IS NOT NULL THEN n.importance ELSE 0.5 END) as weight
    ORDER BY weight DESC LIMIT 10
    """
    
    return await execute_query(cypher, {"user_id": user_id, "terms": terms[:5]})

async def add_interaction(user_id: str, query: str, response: str, intent: str, sync: bool = True):
    """Creates a knowledge node for a user interaction."""
    cypher = """
    MERGE (u:User {id: $user_id})
    CREATE (i:Interaction {
        text: $query,
        response: $response,
        timestamp: datetime(),
        intent: $intent
    })
    CREATE (u)-[:PERFORMED]->(i)
    """
    if sync:
        await execute_query(cypher, {"user_id": user_id, "query": query, "response": response, "intent": intent})
    else:
        asyncio.create_task(execute_query(cypher, {"user_id": user_id, "query": query, "response": response, "intent": intent}))

import asyncio
import time
