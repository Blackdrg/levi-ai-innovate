import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.db.neo4j_db import execute_query

logger = logging.getLogger(__name__)

class GraphEngine:
    """
    Sovereign Knowledge Graph Engine v8.
    Orchestrates subject-relation-object triplets and connects disparate facts.
    """

    async def upsert_triplet(self, user_id: str, subject: str, relation: str, obj: str):
        """
        Inserts or updates a cognitive triplet in the user's personal knowledge graph.
        """
        query = (
            "MERGE (s:Entity {name: $subject, user_id: $user_id}) "
            "MERGE (o:Entity {name: $object, user_id: $user_id}) "
            "MERGE (s)-[r:RELATION {type: $relation}]->(o) "
            "SET r.updated_at = $timestamp, s.updated_at = $timestamp, o.updated_at = $timestamp "
            "RETURN r"
        )
        params = {
            "user_id": user_id,
            "subject": subject.strip().lower(),
            "relation": relation.strip().upper(),
            "object": obj.strip().lower(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await execute_query(query, params)
        logger.debug(f"[GraphEngine] Triplet Upsert: ({subject})-[{relation}]->({obj}) for {user_id}")

    async def get_connected_resonance(self, user_id: str, query_text: str, depth: int = 1) -> List[Dict[str, Any]]:
        """
        Finds entities in the query and returns their neighbors to provide lateral context.
        """
        if not query_text:
            return []

        # Simple entity extraction (v8 fallback: lowercase matches)
        entities = [w.strip(",.?!") for w in query_text.lower().split() if len(w) > 3]
        
        if not entities:
            return []

        cypher = (
            "MATCH (e:Entity)-[r:RELATION]-(neighbor:Entity) "
            "WHERE e.user_id = $user_id AND e.name IN $entities "
            "RETURN DISTINCT neighbor.name AS entity, type(r) AS relation, e.name AS source "
            "LIMIT 10"
        )
        params = {"user_id": user_id, "entities": entities}
        
        results = await execute_query(cypher, params)
        
        resonance = []
        for res in results:
            resonance.append({
                "fact": f"{res['source']} {res['relation']} {res['entity']}",
                "type": "graph_triplet",
                "source": "memory_graph"
            })
            
        return resonance

    async def get_entity_profile(self, user_id: str, entity_name: str) -> Dict[str, Any]:
        """Returns all known relationships for a specific entity."""
        cypher = (
            "MATCH (e:Entity)-[r:RELATION]-(neighbor:Entity) "
            "WHERE e.user_id = $user_id AND e.name = $entity_name "
            "RETURN neighbor.name AS name, type(r) AS relation, labels(neighbor) AS type"
        )
        params = {"user_id": user_id, "entity_name": entity_name.lower()}
        
        results = await execute_query(cypher, params)
        return {"entity": entity_name, "relationships": results}
