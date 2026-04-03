import logging
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from backend.engines.memory.graph_engine import GraphEngine
from backend.core.orchestrator_types import AgentBase, AgentResult

logger = logging.getLogger(__name__)

class RelationInput(BaseModel):
    objective: str = Field(..., description="The mission objective to find relations for.")
    user_id: str = Field(..., description="The user's unique identifier.")
    depth: int = Field(default=2, description="Traversal depth for graph exploration.")

class RelationAgentV8(AgentBase):
    """
    Sovereign v8.6 Relation Explorer.
    Specialized in Knowledge Graph traversal to identify non-obvious mission context.
    """
    
    def __init__(self):
        super().__init__(
            name="relation_agent",
            description="Explores the user Knowledge Graph to find relational context and hidden entity connections."
        )
        self.graph = GraphEngine()

    async def _execute_system(self, input_data: RelationInput, context: Dict[str, Any]) -> AgentResult:
        """
        Performs a multi-degree traversal to find entities related to the mission objective.
        """
        logger.info(f"[RelationAgent] Exploring graph for: {input_data.objective}")
        
        # 1. Identify core entities in the objective (Heuristic/LLM extraction could also be used)
        # For now, we perform a broader 'resonance' search based on the objective keywords
        potential_entities = input_data.objective.split()
        all_relations = []
        
        for entity_name in potential_entities:
            if len(entity_name) < 4: continue # Skip short noise
            relations = await self.graph.get_connected_resonance(
                input_data.user_id, 
                entity_name, 
                depth=input_data.depth
            )
            all_relations.extend(relations)

        if not all_relations:
            return AgentResult(
                id=self.name,
                message="No direct relational connections found in the knowledge graph for this objective.",
                success=True,
                data={"relations_count": 0}
            )

        # 2. Format findings for the brain
        formatted_relations = "\n".join([
            f"- {r['name']} (connected via {len(r['relationships'])} hops)" 
            for r in all_relations[:10]
        ])
        
        summary_message = (
            f"Knowledge Graph Exploration found {len(all_relations)} related entities:\n"
            f"{formatted_relations}\n\n"
            "This indicates a high degree of intersection between the current mission and prior knowledge."
        )

        return AgentResult(
            id=self.name,
            message=summary_message,
            success=True,
            data={
                "relations": all_relations,
                "relations_count": len(all_relations)
            }
        )
