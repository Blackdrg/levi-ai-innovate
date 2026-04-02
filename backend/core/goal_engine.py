"""
Sovereign Goal Engine v8.
Transforms user intent and perception into a formal cognitive goal.
"""

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

    def dict(self, *args, **kwargs):
        # Compatibility with older pydantic versions if needed
        return super().model_dump(*args, **kwargs)

class GoalEngine:
    """
    LeviBrain v8: Goal Engine
    Transforms user intent and perception into a formal cognitive goal.
    """

    async def create_goal(self, perception: Dict[str, Any]) -> Goal:
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        complexity = intent.complexity_level if intent else 2
        
        # 1. Objective Formulation
        objective = self._formulate_objective(perception)
        
        # 2. Success Criteria Generation
        success_criteria = self._generate_success_criteria(intent_type, complexity)
        
        # 3. Priority Calculation (Sovereign Level)
        priority = "high" if complexity >= 3 else "medium"
        
        return Goal(
            objective=objective,
            success_criteria=success_criteria,
            priority=priority
        )

    def _formulate_objective(self, perception: Dict[str, Any]) -> str:
        input_text = perception.get("input", "")
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        
        if intent_type == "search":
            return f"Answer with latest data: {input_text}"
        elif intent_type == "document":
            return f"Extract context and answer query: {input_text}"
        elif intent_type == "code":
            return f"Build/Debug code solution: {input_text}"
        elif intent_type == "image":
            return f"Visualize creative concept: {input_text}"
        
        return f"Synthesize coherent response: {input_text}"

    def _generate_success_criteria(self, intent_type: str, complexity: int) -> List[str]:
        criteria = ["Syntactic coherence", "Factual alignment"]
        
        if intent_type == "search":
             criteria.append("Citations included")
             criteria.append("Real-time relevance")
        elif intent_type == "code":
             criteria.append("Syntactical correctness")
             criteria.append("Logic verification (TDD)")
        elif intent_type == "creative":
             criteria.append("Philosophical resonance")
        
        if complexity >= 3:
             criteria.append("Cross-engine validation")
             
        return criteria
