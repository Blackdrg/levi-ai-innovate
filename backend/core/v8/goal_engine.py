import logging
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from .learning import FragilityTracker

class Goal(BaseModel):
    goal_id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:6]}")
    objective: str
    success_criteria: List[str] = Field(default_factory=list)
    priority: str = "medium"
    state: str = "active"
    self_correction_weight: float = 0.5 # v8.7 Evolutionary weight

class GoalEngine:
    """
    LeviBrain v8.7: Evolutionary Goal Engine
    Adapts mission parameters based on historical resonance and system fragility.
    """

    async def create_goal(self, perception: Dict[str, Any]) -> Goal:
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        complexity = intent.complexity_level if intent else 2
        user_input = perception.get("input", "")
        user_id = perception.get("user_id", "default_user")
        context = perception.get("context", {})
        
        # 1. Pull Evolutionary Metrics
        fragility = FragilityTracker.get_fragility(user_id, intent_type)
        prototypes = context.get("long_term", {}).get("traits", []) # Prototypes stored in traits tier 
        
        # 2. Objective Formulation (Evolutionary)
        objective = await self._formulate_evolutionary_objective(user_input, intent_type, prototypes)
        
        # 3. Dynamic Success Criteria
        success_criteria = self._generate_success_criteria(intent_type, complexity, fragility)
        
        # 4. Self-Correction Weighting
        # Base weight (0.2-1.0) scaled by complexity and fragility
        sc_weight = min(1.0, 0.3 + (complexity * 0.1) + (fragility * 0.4))
        
        priority = self._calculate_priority(complexity, intent_type)
        
        return Goal(
            objective=objective,
            success_criteria=success_criteria,
            priority=priority,
            state="active",
            self_correction_weight=sc_weight
        )

    async def _formulate_evolutionary_objective(self, user_input: str, intent_type: str, prototypes: List[str]) -> str:
        """Formulates mission with subtle evolutionary reveals."""
        base_obj = f"LeviBrain v8 Mission: {user_input} [Intent: {intent_type.upper()}]"
        
        # Subtle Reveal: If we have a matching reasoning prototype, mention it subtly
        if prototypes:
            relevant_proto = next((p for p in prototypes if f"[{intent_type}]" in p), None)
            if relevant_proto:
                # Reveals it subtly as requested by USER
                reveal = f" (Synthesizing learned reasoning pattern for {intent_type} missions)"
                return f"{base_obj}{reveal}"
                
        return base_obj

    def _generate_success_criteria(self, intent_type: str, complexity: int, fragility: float = 0.0) -> List[str]:
        """Generates criteria with fragility-based hardening."""
        criteria = [
            "Alignment: Logical consistency with user objective.",
            "Grounding: Factual accuracy and source relevance.",
            "Resonance: Cognitive style and tone alignment."
        ]
        
        # Domain-Specific extras
        if intent_type == "search":
             criteria.append("Investigative Depth: Multi-vector source synthesis.")
        elif intent_type == "code":
             criteria.append("Syntactic Correctness: Sandbox-passed logic.")
             if fragility > 0.5: # Hardened requirement if fragile
                 criteria.append("Verification: Mandatory multi-path cross-check (Fragility Mode).")
        
        if complexity >= 3 or fragility > 0.7:
             criteria.append("Cross-Engine Validation: Swarm-based consensus check.")
             
        return criteria

    def _calculate_priority(self, complexity: int, intent_type: str) -> str:
        if complexity >= 4 or intent_type in ["code", "document"]:
             return "high"
        return "medium" if complexity >= 2 else "low"
