"""
Sovereign Graph Knowledge Engine v15.0-GA.
High-fidelity relational memory layer utilizing typed ontology and deep resonance loops.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from backend.db.neo4j_connector import Neo4jStore
from backend.db.ontology import KnowledgeTriplet, Entity, EntityType, Relation, RelationType
from backend.utils.cypher_sanitizer import CypherSanitizer
from backend.db.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

class GraphEngine:
    """
    Sovereign Knowledge Graph Engine v15.0-GA.
    Orchestrates complex relational memory retrieval and persistence.
    """
    def __init__(self):
        self.store = Neo4jStore()

    async def upsert_triplet(self, user_id: str, subject: str, relation: str, obj: str, tenant_id: str = "default", mission_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """
        Sovereign v15.0: Hardened entry point for relational knowledge ingestion.
        Sanitizes input and maps strings to the OS Ontology.
        """
        # 🛡️ Injection Protection: Strip dangerous keywords
        s_clean, r_clean, o_clean = CypherSanitizer.sanitize_triplet(subject, relation, obj)

        # Map relation string → RelationType enum
        try:
            rel_type = RelationType(r_clean.upper().replace(" ", "_"))
        except ValueError:
            rel_type = RelationType.RELATED_TO

        triplet = KnowledgeTriplet(
            subject=Entity(name=s_clean.lower(), type=EntityType.CONCEPT, tenant_id=tenant_id),
            predicate=Relation(
                source=s_clean, 
                target=o_clean, 
                type=rel_type, 
                tenant_id=tenant_id,
                source_mission_id=mission_id
            ),
            object=Entity(name=o_clean.lower(), type=EntityType.CONCEPT, tenant_id=tenant_id),
            source_mission_id=mission_id
        )
        
        await self.store.upsert_triplet(triplet)
        logger.debug(f"[GraphEngine] Triplet ingested: {s_clean} -> {rel_type.value} -> {o_clean}")

    async def get_connected_resonance(self, user_id: str, query_text: str, depth: int = 1) -> List[Dict[str, Any]]:
        """
        Sovereign v15.0: Contextual Resonance Discovery.
        Utilizes Neo4jClient for optimized high-hop traversal and user-interaction resonance.
        """
        if not query_text:
            return []

        # 1. Broad Resonance Search (Interactions + Traits) via Neo4jClient
        client_resonance = await Neo4jClient.get_resonance_entities(user_id, query_text)
        
        # 2. Targeted Ontological Resonance (Entities) via Neo4jStore
        # We look for primary concepts mentioned in the query
        entities = [w.strip(",.?!").lower() for w in query_text.split() if len(w) > 4]
        
        unique_facts = {}
        
        # Process client resonance first (high relevance)
        for res in client_resonance:
            entity = res.get("entity", {})
            labels = res.get("labels", [])
            fact_text = entity.get("text") or entity.get("name")
            if fact_text:
                unique_facts[fact_text] = {
                    "fact": f"Historical Resonance ({labels[0]}): {fact_text}",
                    "importance": res.get("weight", 0.7),
                    "type": "graph_resonance"
                }

        # Sub-process: Deep hop search for primary entities
        tasks = []
        for entity in set(entities):
            tasks.append(self.store.get_resonance(entity, tenant_id=user_id))
        
        store_results = await asyncio.gather(*tasks)
        for entity_results in store_results:
            for res in entity_results:
                fact_text = f"Entity '{res['name']}' ({res['type']}) is contextually linked to your inquiry."
                if fact_text not in unique_facts:
                    unique_facts[fact_text] = {
                        "fact": fact_text,
                        "importance": 0.6, # Slightly lower for raw hops
                        "type": "graph_triplet"
                    }
        
        return list(unique_facts.values())[:15]

    async def delete_mission_nodes(self, mission_id: str):
        """Sovereign v15.0 GA: Targeted lifecycle pruning."""
        await self.store.delete_mission_nodes(mission_id)
        
    async def clear_user_graph(self, user_id: str):
        """Sovereign v15.0 GA: Hardened absolute memory wipe for privacy/compliance."""
        await self.store.clear_user_graph(user_id)

    async def close(self):
        await self.store.close()
