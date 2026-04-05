import requests
import json
import logging
from typing import List, Dict, Any, Optional
from ..db.ontology import KnowledgeTriplet, Entity, EntityType, Relation, RelationType

logger = logging.getLogger(__name__)

class KnowledgeExtractor:
    """
    Sovereign Knowledge Extractor.
    Uses the Local Ollama Brain to distill mission results into structured Neo4j triplets.
    """
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3:latest"

    async def distill_triplets(self, user_input: str, response: str, tenant_id: str = "default") -> List[KnowledgeTriplet]:
        """
        Calls the local LLM to extract Subject-Relation-Object triplets.
        """
        prompt = (
            "You are a Knowledge Graph Architect. Distill the following interaction into a list of structured triplets.\n"
            "Format: Subject | Relation | Object | EntityType(Subject) | EntityType(Object)\n"
            "Relationship types allowed: WORKS_AT, INTERESTED_IN, PART_OF, CREATED_BY, LOCATED_IN, EXECUTES, DEPENDS_ON, RELATED_TO\n"
            "Entity types allowed: PERSON, ORGANIZATION, CONCEPT, TASK, LOCATION, TECHNOLOGY, EVENT\n\n"
            f"User: {user_input}\n"
            f"LEVI: {response}\n\n"
            "Output ONLY JSON list of triplets: [{\"s\": \"\", \"r\": \"\", \"o\": \"\", \"st\": \"\", \"ot\": \"\"}]"
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        try:
            res = requests.post(self.ollama_url, json=payload, timeout=45)
            if res.status_code == 200:
                data = res.json().get("response", "[]")
                triplets_raw = json.loads(data)
                
                triplets = []
                for t in triplets_raw:
                    try:
                        # Map strings to Enums
                        subject_type = EntityType(t["st"].capitalize()) if "st" in t else EntityType.CONCEPT
                        object_type = EntityType(t["ot"].capitalize()) if "ot" in t else EntityType.CONCEPT
                        relation_type = RelationType(t["r"].upper()) if "r" in t else RelationType.RELATED_TO
                        
                        triplet = KnowledgeTriplet(
                            subject=Entity(name=t["s"].lower(), type=subject_type, tenant_id=tenant_id),
                            predicate=Relation(source=t["s"], target=t["o"], type=relation_type, tenant_id=tenant_id),
                            object=Entity(name=t["o"].lower(), type=object_type, tenant_id=tenant_id),
                            tenant_id=tenant_id
                        )
                        triplets.append(triplet)
                    except Exception as ve:
                        logger.warning(f"[KnowledgeExtractor] Validation skipping triplet: {ve}")
                
                return triplets
            else:
                logger.error(f"[KnowledgeExtractor] Ollama error: {res.status_code}")
                return []
        except Exception as e:
            logger.error(f"[KnowledgeExtractor] Extraction failed: {e}")
            return []
