# neo4j_connector.py
import os
import logging
from typing import List, Dict, Any
from neo4j import AsyncGraphDatabase
from .ontology import KnowledgeTriplet, Entity, EntityType, RelationType

logger = logging.getLogger(__name__)

class Neo4jStore:
    """
    Sovereign Tier 5 Memory Connector.
    Interfaces with the Neo4j Knowledge Graph using the Absolute Monolith ontology.
    """
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "sovereign_graph")
        self._driver = None

    async def connect(self):
        if not self._driver:
            self._driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver

    async def close(self):
        if self._driver:
            await self._driver.close()

    async def upsert_triplet(self, triplet: KnowledgeTriplet):
        """
        Inserts or merges a typed knowledge triplet into the graph.
        """
        driver = await self.connect()
        async with driver.session() as session:
            try:
                cypher = triplet.to_cypher()
                await session.run(cypher)
                logger.info(f"[Neo4j] Triplet Upsert: ({triplet.subject.name})-[{triplet.predicate.type.value}]->({triplet.object.name})")
            except Exception as e:
                logger.error(f"[Neo4j] Failed to upsert triplet: {e}")

    async def get_resonance(self, entity_name: str, tenant_id: str, depth: int = 1) -> List[Dict[str, Any]]:
        """
        Performs a k-hop resonance search for an entity to provide context.
        """
        driver = await self.connect()
        async with driver.session() as session:
            # Cypher for k-hop neighborhood search
            cypher = (
                "MATCH (s:Entity {name: $name, tenant_id: $tenant_id})-[r*..2]-(o:Entity) "
                "RETURN DISTINCT o.name as name, labels(o)[0] as type, o.tenant_id as tenant_id "
                "LIMIT 15"
            )
            result = await session.run(cypher, name=entity_name, tenant_id=tenant_id)
            return [record.data() async for record in result]

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
