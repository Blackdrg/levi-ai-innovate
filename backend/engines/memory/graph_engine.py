import os
import logging
from typing import List, Dict, Any, Optional
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class GraphEngine:
    """
    Sovereign Relational Memory Engine (Neo4j).
    Manages Subject-Predicate-Object triplets for high-fidelity reasoning.
    """

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "levi_pass_graph")
        self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))

    async def close(self):
        await self.driver.close()

    async def upsert_triplet(self, user_id: str, subject: str, relation: str, obj: str, metadata: Dict[str, Any] = None):
        """
        Idempotently inserts or updates a triplet in the Knowledge Graph.
        """
        async with self.driver.session() as session:
            query = (
                "MERGE (u:User {uid: $user_id}) "
                "MERGE (s:Entity {name: $subject, user_id: $user_id}) "
                "MERGE (o:Entity {name: $obj, user_id: $user_id}) "
                "MERGE (u)-[:HAS_ENTITY]->(s) "
                "MERGE (s)-[r:RELATION {type: $relation}]->(o) "
                "SET r.updated_at = timestamp(), r.metadata = $metadata "
                "RETURN s, r, o"
            )
            try:
                await session.run(query, user_id=user_id, subject=subject, relation=relation.upper(), obj=obj, metadata=json.dumps(metadata or {}))
                logger.debug(f"[GraphEngine] Triplet engrained: ({subject})-[{relation}]->({obj})")
            except Exception as e:
                logger.error(f"[GraphEngine] Failed to upsert triplet: {e}")

    async def get_connected_resonance(self, user_id: str, concept: str, depth: int = 2) -> List[Dict[str, Any]]:
        """
        Hardened v8.12: Traverses the Knowledge Graph up to 'depth' degrees.
        Returns a list of connected entities and their relationship types.
        """
        async with self.driver.session() as session:
            # Traversal query: Find all nodes connected to 'concept' within 'depth' hops
            query = (
                "MATCH (s:Entity {name: $concept, user_id: $user_id}) "
                "MATCH path = (s)-[*1..$depth]-(related:Entity) "
                "WHERE related.user_id = $user_id "
                "WITH related, relationships(path) as rels, length(path) as hops "
                "RETURN DISTINCT related.name as name, [r in rels | type(r)] as types, hops "
                "ORDER BY hops ASC LIMIT 20"
            )
            try:
                result = await session.run(query, user_id=user_id, concept=concept, depth=depth)
                records = await result.data()
                return records
            except Exception as e:
                logger.error(f"[GraphEngine] Failed to retrieve connected resonance: {e}")
                return []

    async def get_entity_context(self, user_id: str, entity_name: str) -> Dict[str, Any]:
        """
        Retrieves the immediate neighborhood of an entity for rich status context.
        """
        async with self.driver.session() as session:
            query = (
                "MATCH (e:Entity {name: $entity_name, user_id: $user_id}) "
                "MATCH (e)-[r:RELATION]->(neighbor:Entity) "
                "RETURN type(r) as relation, neighbor.name as neighbor, r.metadata as metadata"
            )
            try:
                result = await session.run(query, user_id=user_id, entity_name=entity_name)
                records = await result.data()
                return {
                    "entity": entity_name,
                    "relationships": records,
                    "count": len(records)
                }
            except Exception as e:
                logger.error(f"[GraphEngine] Failed to get entity context: {e}")
                return {"entity": entity_name, "relationships": [], "count": 0}

    async def get_user_schema(self, user_id: str) -> Dict[str, Any]:
        """Returns a summary of the user's current knowledge graph structure."""
        async with self.driver.session() as session:
            query = (
                "MATCH (s:Entity {user_id: $user_id})-[r:RELATION]->(o:Entity) "
                "RETURN s.name as subject, type(r) as relation, o.name as object"
            )
            result = await session.run(query, user_id=user_id)
            return await result.data()

import json # For metadata serialization
