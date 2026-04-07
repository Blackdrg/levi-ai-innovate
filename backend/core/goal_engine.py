"""
Sovereign Goal Engine v14.0.
Transforms user intent and brain policy into a formal cognitive goal.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from .orchestrator_types import BrainDecision, BrainMode

logger = logging.getLogger(__name__)

class Goal(BaseModel):
    goal_id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:6]}")
    objective: str
    success_criteria: List[str] = Field(default_factory=list)
    validators: List[Dict[str, Any]] = Field(default_factory=list) # Machine-verifiable rules
    metrics: Dict[str, Any] = Field(default_factory=dict) # Quantitative targets
    priority: str = "medium"
    state: str = "active"
    mode: Optional[str] = None

    def dict(self, *args, **kwargs):
        # Compatibility with older pydantic versions if needed
        return super().model_dump(*args, **kwargs)

class GoalEngine:
    """
    LeviBrain v14.0: Goal Engine.
    Subservient to the Brain Policy Engine.
    """

    async def create_goal(self, perception: Dict[str, Any], decision: Optional[BrainDecision] = None) -> Goal:
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        complexity = intent.complexity_level if intent else 2
        
        # 1. Mode-Driven Objective Formulation
        mode = decision.mode if decision else BrainMode.BALANCED
        objective = self._formulate_objective(perception, mode)
        
        # 2. Policy-Driven Success Criteria & Validators Generation
        success_criteria, validators, metrics = self._generate_criteria(intent_type, complexity, perception.get("input", ""), mode)
        
        # 3. Priority Calculation
        priority = "high" if (complexity >= 3 or mode in [BrainMode.DEEP, BrainMode.SECURE]) else "medium"
        
        return Goal(
            objective=objective,
            success_criteria=success_criteria,
            validators=validators,
            metrics=metrics,
            priority=priority,
            mode=mode.value
        )

    def _formulate_objective(self, perception: Dict[str, Any], mode: BrainMode) -> str:
        input_text = perception.get("input", "")
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        
        prefix = f"[{mode.value}] "
        
        if mode == BrainMode.SECURE:
             return f"{prefix}Securely process restricted query: {input_text}"
             
        if intent_type == "search":
            return f"{prefix}Retrieve and distill latest data: {input_text}"
        elif intent_type == "document":
            return f"{prefix}Synthesize document insights: {input_text}"
        elif intent_type == "code":
            return f"{prefix}Architect and verify code solution: {input_text}"
        elif intent_type == "image":
            return f"{prefix}Render high-fidelity creative concept: {input_text}"
        
        return f"{prefix}Synthesize coherent response: {input_text}"

    def _generate_criteria(self, intent_type: str, complexity: int, user_input: str, mode: BrainMode) -> tuple:
        criteria = ["Syntactic coherence", "Factual alignment"]
        validators = []
        metrics = {"min_confidence": 0.8}
        
        # Mode-based constraints
        if mode == BrainMode.FAST:
            criteria.append("Latency < 1000ms")
            metrics["max_latency_ms"] = 1000
        elif mode == BrainMode.DEEP:
            criteria = ["Logical chain validation", "Comprehensive synthesis", "Cross-domain resonance"]
            metrics["min_confidence"] = 0.95
        elif mode == BrainMode.SECURE:
            criteria.append("PII isolation")
            validators.append({"type": "sandbox_check", "level": "high"})
        
        # Intent-based rules
        if intent_type == "search":
             criteria.append("Citations included")
             validators.append({"type": "regex", "pattern": r"\[\d+\]|https?://", "field": "response"})
             metrics["min_sources"] = 2
        elif intent_type == "code":
             criteria.append("Syntactical correctness")
             validators.append({"type": "python_check", "field": "code"})
             metrics["max_latency_ms"] = 5000
             
        return criteria, validators, metrics
