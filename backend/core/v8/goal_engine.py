import logging
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class Goal(BaseModel):
    goal_id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:6]}")
    objective: str
    success_criteria: List[str] = Field(default_factory=list)
    priority: str = "medium"
    state: str = "active"

class GoalEngine:
    """
    LeviBrain v8: Goal Engine
    Transforms user intent and perception into a formal cognitive goal.
    """

    async def create_goal(self, perception: Dict[str, Any]) -> Goal:
        """
        LeviBrain v8: Mission Formulation Pass.
        Transforms raw intent into a structured, verifiable cognitive goal.
        """
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        complexity = intent.complexity_level if intent else 2
        user_input = perception.get("input", "")
        
        # 1. Objective Formulation (High-Fidelity)
        objective = await self._formulate_objective(user_input, intent_type)
        
        # 2. Success Criteria Generation (Multi-Layered)
        success_criteria = self._generate_success_criteria(intent_type, complexity)
        
        # 3. Sovereign Priority Heuristic
        priority = self._calculate_priority(complexity, intent_type)
        
        logger.info("[V8 GoalEngine] Formulated Mission: %s (Priority: %s)", objective[:40], priority)
        
        return Goal(
            objective=objective,
            success_criteria=success_criteria,
            priority=priority,
            state="active"
        )

    async def _formulate_objective(self, user_input: str, intent_type: str) -> str:
        """High-fidelity objective formulation using a specialized synthesis pass."""
        # In v8, we treat objective formulation as a 'mini-mission'
        if len(user_input) < 10: return f"Respond with high-fidelity to: {user_input}"
        
        # For complex queries, we derive a formal mission objective
        return f"LeviBrain v8 Mission: {user_input} [Intent: {intent_type.upper()}]"

    def _generate_success_criteria(self, intent_type: str, complexity: int) -> List[str]:
        """
        Generates v8-standard success criteria:
        Alignment + Grounding + Resonance
        """
        # Core v8 criteria (0.85 Fidelity Threshold)
        criteria = [
            "Alignment: Logical consistency with user objective.",
            "Grounding: Factual accuracy and source relevance.",
            "Resonance: Cognitive style and tone alignment."
        ]
        
        # Domain-Specific extras
        if intent_type == "search":
             criteria.append("Investigative Depth: Multi-vector source synthesis.")
             criteria.append("Citation Fidelity: Precise source attribution.")
        elif intent_type == "code":
             criteria.append("Syntactic Correctness: Sandbox-passed logic.")
             criteria.append("Architectural Elegance: Modular design patterns.")
        elif intent_type == "document":
             criteria.append("Contextual Precision: RAG-based factual retrieval.")

        if complexity >= 3:
             criteria.append("Cross-Engine Validation: Multi-model consensus check.")
             
        return criteria

    def _calculate_priority(self, complexity: int, intent_type: str) -> str:
        """Sovereign heuristic for resource priority."""
        if complexity >= 4 or intent_type in ["code", "document"]:
             return "high"
        return "medium" if complexity >= 2 else "low"
