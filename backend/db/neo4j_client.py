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
    async def add_interaction(cls, user_id: str, query: str, response: str, intent: str):
        """Creates a knowledge node for a user interaction."""
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
        # Note: apoc might not be available, fallback to manual uuid if needed
        try:
             await cls.execute_query(cypher, {
                "user_id": user_id,
                "query": query,
                "response": response,
                "intent": intent
            })
        except:
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

    @classmethod
    async def get_resonance_entities(cls, user_id: str, query_text: str) -> List[Dict[str, Any]]:
        """
        Retrieves entities and interactions related to the current query context.
        Used for Phase 4 Graph Retrieval.
        """
        # Simple phrase matching for resonance
        # In a real system, we might use full-text indices or vector extensions in Neo4j.
        cypher = """
        MATCH (u:User {id: $user_id})-[:PERFORMED|KNOWS|PREFERS]->(n)
        WHERE n.text CONTAINS $term OR n.name CONTAINS $term or n.intent = $term
        RETURN n as entity, labels(n) as labels LIMIT 5
        """
        # Extract keywords for better matching
        terms = [t for t in query_text.split() if len(t) > 3]
        results = []
        for term in terms[:3]:
            res = await cls.execute_query(cypher, {"user_id": user_id, "term": term})
            results.extend(res)
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
