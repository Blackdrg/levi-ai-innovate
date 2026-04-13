import logging
import asyncio
from typing import Dict, Any, List
from backend.db.neo4j_connector import Neo4jStore
from backend.db.ontology import KnowledgeTriplet, Entity, EntityType, Relation, RelationType
from backend.utils.cypher_sanitizer import CypherSanitizer

logger = logging.getLogger(__name__)

class GraphEngine:
    """
    Sovereign Knowledge Graph Engine v13.
    High-fidelity relational memory layer utilizing typed ontology.
    """
    def __init__(self):
        self.store = Neo4jStore()

    async def upsert_triplet(self, user_id: str, subject: str, relation: str, obj: str, tenant_id: str = "default"):
        """
        Standard v13 Bridge: Distils strings into typed triplets and merges into graph.
        Maps the relation string to a RelationType enum value; unknown values default to RELATED_TO.
        """
        # v14.0.0 Injection Protection: Strip dangerous keywords from LLM-provided values
        s_clean, r_clean, o_clean = CypherSanitizer.sanitize_triplet(subject, relation, obj)

        # Map relation string → RelationType enum
        try:
            rel_type = RelationType(r_clean.upper())
        except ValueError:
            rel_type = RelationType.RELATED_TO

        triplet = KnowledgeTriplet(
            subject=Entity(name=s_clean.lower(), type=EntityType.CONCEPT, tenant_id=tenant_id),
            predicate=Relation(source=s_clean, target=o_clean, type=rel_type, tenant_id=tenant_id),
            object=Entity(name=o_clean.lower(), type=EntityType.CONCEPT, tenant_id=tenant_id),
        )
        await self.store.upsert_triplet(triplet)

    async def get_connected_resonance(self, user_id: str, query_text: str, depth: int = 1) -> List[Dict[str, Any]]:
        """
        Finds primary entities and their secondary neighbors (2-hop) to hydrate context.
        """
        if not query_text:
            return []

        # 1. Entity Extraction (v13 Enhanced)
        # We look for capitalized words or known concepts
        entities = [w.strip(",.?!").lower() for w in query_text.split() if len(w) > 3]
        
        resonance = []
        tasks = []
        for entity in set(entities):
            tasks.append(self.store.get_resonance(entity, tenant_id="default"))
        
        results = await asyncio.gather(*tasks)
        
        for entity_results in results:
            for res in entity_results:
                resonance.append({
                    "fact": f"Graph Relation: {res['name']} ({res['type']}) is linked to your current context.",
                    "type": "graph_triplet",
                    "source": "memory_graph",
                    "importance": 0.8
                })
        
        # Deduplicate and limit
        seen = set()
        unique_resonance = []
        for r in resonance:
            if r["fact"] not in seen:
                unique_resonance.append(r)
                seen.add(r["fact"])
        
        return unique_resonance[:15]

    async def close(self):
        await self.store.close()
    async def delete_mission_nodes(self, mission_id: str):
        """
        Sovereign v14.2: Targeted graph pruning.
        Purges all nodes and relationships associated with a specific mission ID.
        """
        if not mission_id: return
        cypher = "MATCH (n {mission_id: $mid}) DETACH DELETE n"
        # We need a way to run raw cypher via Neo4jStore
        if hasattr(self.store, 'run_query'):
            await self.store.run_query(cypher, {"mid": mission_id})
        else:
            # Fallback for manual session management if run_query is missing
            driver = await self.store.connect()
            async with driver.session() as session:
                await session.run(cypher, mid=mission_id)
        
        logger.info(f"[GraphEngine] Purged nodes for mission {mission_id}")
