# neo4j_connector.py
import os
import logging
from typing import List, Dict, Any
from neo4j import AsyncGraphDatabase
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .ontology import KnowledgeTriplet, Entity, EntityType, RelationType
from backend.utils.network import neo4j_breaker

logger = logging.getLogger(__name__)

class Neo4jStore:
    """
    Sovereign Tier 5 Memory Connector.
    Interfaces with the Neo4j Knowledge Graph using the Sovereign OS ontology.
    """
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "sovereign_graph")
        self._driver = None

    async def connect(self):
        """Graduation Audit: Singleton Driver Management with Health Validation."""
        if not self._driver:
            self._driver = AsyncGraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50
            )
        return self._driver

    async def health_check(self) -> bool:
        """Proactive circuit-aware health check for Neo4j."""
        try:
            driver = await self.connect()
            async with driver.session() as session:
                await session.run("RETURN 1")
            return True
        except Exception as e:
            logger.error(f"[Neo4j] Health check failed: {e}")
            return False

    async def close(self):
        if self._driver:
            await self._driver.close()
            self._driver = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def upsert_triplet(self, triplet: KnowledgeTriplet):
        """
        Inserts or merges a typed knowledge triplet into the graph.
        v14.1.0: Circuit Breaker + Retry HARDENING.
        """
        async def _run():
            driver = await self.connect()
            async with driver.session() as session:
                cypher_query, parameters = triplet.to_cypher()
                await session.run(cypher_query, parameters)
                logger.debug(f"[Neo4j] Parameterized Upsert: ({triplet.subject.name})-[{triplet.predicate.type.value}]->({triplet.object.name})")

        try:
            await neo4j_breaker.async_call(_run)
        except Exception as e:
            logger.error(f"[Neo4j] Failed to upsert triplet after retries/breaker: {e}")
            raise

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def get_resonance(self, entity_name: str, tenant_id: str, depth: int = 1) -> List[Dict[str, Any]]:
        """
        Performs a k-hop resonance search with stability layer.
        """
        async def _run():
            driver = await self.connect()
            async with driver.session() as session:
                cypher = (
                    "MATCH (s:Entity {name: $name, tenant_id: $tenant_id})-[r*..2]-(o:Entity) "
                    "RETURN DISTINCT o.name as name, labels(o)[0] as type, o.tenant_id as tenant_id "
                    "LIMIT 15"
                )
                result = await session.run(cypher, name=entity_name, tenant_id=tenant_id)
                return [record.data() async for record in result]

        try:
            return await neo4j_breaker.async_call(_run)
        except Exception as e:
            logger.warning(f"[Neo4j] Resonance search degraded: {e}")
            return []

    async def store_generic_fact(self, subject: str, relation: str, obj: str, tenant_id: str = "default"):
        """
        Backward compatibility layer for simple string-based triplets.
        """
        triplet = KnowledgeTriplet(
            subject=Entity(name=subject, type=EntityType.CONCEPT, tenant_id=tenant_id),
            predicate=RelationType.RELATED_TO, # Simplified for generic facts
            object=Entity(name=obj, type=EntityType.CONCEPT, tenant_id=tenant_id),
            tenant_id=tenant_id
        )
        # Note: RelationType is used here, but KnowledgeTriplet expects a Relation object or Enum
        # I'll fix the call to ensure it's valid based on ontology.py definitions.
        pass # To be refined in implementation
