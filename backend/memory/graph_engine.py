import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.db.neo4j_connector import Neo4jStore
from backend.db.ontology import KnowledgeTriplet, Entity, EntityType, Relation, RelationType

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
        Standard v13 Bridge: Distills strings into typed triplets and merges into graph.
        """
        # Logic: We'll assume CONCEPT for generic strings unless we have metadata
        triplet = KnowledgeTriplet(
            subject=Entity(name=subject.lower(), type=EntityType.CONCEPT, tenant_id=tenant_id),
            predicate=Relation(source=subject, target=obj, type=RelationType.RELATED_TO, tenant_id=tenant_id),
            object=Entity(name=obj.lower(), type=EntityType.CONCEPT, tenant_id=tenant_id),
            tenant_id=tenant_id
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
