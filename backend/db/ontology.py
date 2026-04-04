from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class EntityType(str, Enum):
    PERSON = "Person"
    ORGANIZATION = "Organization"
    CONCEPT = "Concept"
    TASK = "Task"
    LOCATION = "Location"
    TECHNOLOGY = "Technology"
    EVENT = "Event"
    UNKNOWN = "Unknown"

class RelationType(str, Enum):
    WORKS_AT = "WORKS_AT"
    INTERESTED_IN = "INTERESTED_IN"
    PART_OF = "PART_OF"
    CREATED_BY = "CREATED_BY"
    LOCATED_IN = "LOCATED_IN"
    EXECUTES = "EXECUTES"
    DEPENDS_ON = "DEPENDS_ON"
    RELATED_TO = "RELATED_TO"

class Entity(BaseModel):
    name: str = Field(..., description="Unique name/identifier of the entity")
    type: EntityType = Field(default=EntityType.UNKNOWN)
    tenant_id: str = Field(..., description="Tenant isolation scope")
    source_mission_id: Optional[str] = Field(None, description="Mission that discovered this entity")
    properties: dict = Field(default_factory=dict)

class Relation(BaseModel):
    source: str = Field(..., description="Source entity name")
    target: str = Field(..., description="Target entity name")
    type: RelationType = Field(default=RelationType.RELATED_TO)
    tenant_id: str = Field(..., description="Tenant isolation scope")
    source_mission_id: Optional[str] = Field(None, description="Mission that established this link")
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: Optional[str] = Field(None, description="Source of this fact")

class KnowledgeTriplet(BaseModel):
    """
    Sovereign Tier 5 Knowledge Unit.
    Statically typed, validated, and tenant-scoped.
    """
    subject: Entity
    predicate: Relation
    object: Entity
    source_mission_id: Optional[str] = Field(None, description="Mission originating this triplet")

    def to_cypher(self) -> str:
        """Generates a Neo4j Cypher query for this triplet."""
        return (
            f"MERGE (s:{self.subject.type.value} {{name: '{self.subject.name}', tenant_id: '{self.subject.tenant_id}'}}) "
            f"ON CREATE SET s.mission_id = '{self.source_mission_id or ''}' "
            f"MERGE (o:{self.object.type.value} {{name: '{self.object.name}', tenant_id: '{self.object.tenant_id}'}}) "
            f"ON CREATE SET o.mission_id = '{self.source_mission_id or ''}' "
            f"MERGE (s)-[r:{self.predicate.type.value} {{tenant_id: '{self.predicate.tenant_id}', weight: {self.predicate.weight}, mission_id: '{self.source_mission_id or ''}'}}]->(o)"
        )
