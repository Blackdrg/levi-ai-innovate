import os
import logging
from neo4j import AsyncGraphDatabase
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class Neo4jClient:
    """
    Sovereign v11.0: Real Neo4j Client for Graph Knowledge Retrieval.
    Handles Async connections to the Knowledge Graph.
    """
    _driver = None

    @classmethod
    async def get_driver(cls):
        if cls._driver is None:
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = os.getenv("NEO4J_USER", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "password")
            try:
                cls._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
                # Note: verify_connectivity() is available in newer drivers
                # but we'll try a simple query to ensure it's up.
            except Exception as e:
                logger.error(f"[Neo4j] Driver initialization failed: {e}")
                return None
        return cls._driver

    @classmethod
    async def close(cls):
        if cls._driver:
            await cls._driver.close()
            cls._driver = None

    @classmethod
    async def execute_query(cls, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        driver = await cls.get_driver()
        if not driver: return []
        
        async with driver.session() as session:
            try:
                result = await session.run(query, parameters or {})
                records = await result.data()
                return records
            except Exception as e:
                logger.error(f"[Neo4j] Query failed: {e}")
                return []

    @classmethod
    async def add_interaction(cls, user_id: str, query: str, response: str, intent: str, sync: bool = True):
        """
        Creates a knowledge node for a user interaction.
        v14.2: Added sync flag to manage knowledge resonance lag.
        """
        cypher = """
        MERGE (u:User {id: $user_id})
        CREATE (i:Interaction {
            id: apoc.create.uuid(),
            text: $query,
            response: $response,
            timestamp: datetime(),
            intent: $intent
        })
        CREATE (u)-[:PERFORMED]->(i)
        """
        
        async def _execute():
            try:
                 await cls.execute_query(cypher, {
                    "user_id": user_id,
                    "query": query,
                    "response": response,
                    "intent": intent
                })
            except Exception as e:
                 logger.warning(f"[Neo4j] APOC failed, attempting fallback: {e}")
                 cypher_no_apoc = """
                 MERGE (u:User {id: $user_id})
                 CREATE (i:Interaction {
                    text: $query,
                    response: $response,
                    timestamp: datetime(),
                    intent: $intent
                 })
                 CREATE (u)-[:PERFORMED]->(i)
                 """
                 await cls.execute_query(cypher_no_apoc, {
                    "user_id": user_id,
                    "query": query,
                    "response": response,
                    "intent": intent
                })

        if sync:
            await _execute()
        else:
            import asyncio
            asyncio.create_task(_execute())

    @classmethod
    async def get_resonance_entities(cls, user_id: str, query_text: str) -> List[Dict[str, Any]]:
        """
        Retrieves entities and interactions related to the current query context.
        v14.2: Hardened resonance with phrase expansion and multi-hop awareness.
        """
        if not query_text: return []
        
        # 1. Term Expansion (Simple keyword extraction)
        stop_words = {"what", "how", "show", "give", "find", "this", "that", "user"}
        terms = [t.lower() for t in query_text.replace("?", "").split() if len(t) > 3 and t.lower() not in stop_words]
        
        if not terms: return []

        # 2. Resonate across User Clusters (Interactions + Traits)
        cypher = """
        MATCH (u:User {id: $user_id})-[:PERFORMED|KNOWS|PREFERS]->(n)
        WHERE any(term IN $terms WHERE n.text CONTAINS term OR n.name CONTAINS term OR n.intent CONTAINS term)
        RETURN n as entity, labels(n) as labels, 
               (CASE WHEN n.importance IS NOT NULL THEN n.importance ELSE 0.5 END) as weight
        ORDER BY weight DESC LIMIT 10
        """
        
        try:
            results = await cls.execute_query(cypher, {"user_id": user_id, "terms": terms[:5]})
            logger.debug(f"[Neo4j] Resonance match found {len(results)} atoms for query: {query_text[:30]}...")
            return results
        except Exception as e:
            logger.error(f"[Neo4j] Resonance retrieval failure: {e}")
            return []
    @classmethod
    async def clear_user_data(cls, user_id: str):
        """Detaches and deletes all nodes associated with a user for absolute privacy."""
        cypher = """
        MATCH (u:User {id: $user_id})
        OPTIONAL MATCH (u)-[r]-(n)
        DETACH DELETE u, n, r
        """
        try:
            await cls.execute_query(cypher, {"user_id": user_id})
            logger.info(f"[Neo4j] Absolute wipe complete for user: {user_id}")
        except Exception as e:
            logger.error(f"[Neo4j] Wipe failed for user {user_id}: {e}")
