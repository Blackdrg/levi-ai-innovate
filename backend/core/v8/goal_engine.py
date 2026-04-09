import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from .learning import FragilityTracker

class Goal(BaseModel):
    goal_id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:6]}")
    user_id: str = "default_user"
    objective: str
    success_criteria: List[str] = Field(default_factory=list)
    priority: str = "medium"
    state: str = "active" # active, completed, failed, pending
    self_correction_weight: float = 0.5
    is_long_horizon: bool = False
    parent_goal_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class GoalEngine:
    """
    LEVI-AI Sovereign OS v14.0.0-Autonomous-SOVEREIGN [ACTIVE V14 COMPONENT].
    Evolutionary Goal Engine: Adapts mission parameters based on historical resonance and DCN status.
    """

    async def create_goal(self, perception: Dict[str, Any]) -> Goal:
        intent = perception.get("intent")
        intent_type = intent.intent_type if intent else "chat"
        complexity = intent.complexity_level if intent else 2
        user_input = perception.get("input", "")
        user_id = perception.get("user_id", "default_user")
        context = perception.get("context", {})

        # 0. Check for existing Long-Horizon Objective
        is_long = any(k in user_input.lower() for k in ["long-term", "plan", "roadmap", "weeks", "months"])
        
        # 1. Pull Evolutionary Metrics
        fragility = FragilityTracker.get_fragility(user_id, intent_type)
        prototypes = context.get("long_term", {}).get("traits", []) 
        
        # 2. Objective Formulation (Evolutionary)
        objective = await self._formulate_evolutionary_objective(user_input, intent_type, prototypes)
        
        # 3. Dynamic Success Criteria (v13.0 Hardened)
        success_criteria = self._generate_success_criteria(intent_type, complexity, fragility)
        
        # 4. Self-Correction Weighting
        sc_weight = min(1.0, 0.3 + (complexity * 0.1) + (fragility * 0.4))
        
        priority = self._calculate_priority(complexity, intent_type)
        
        goal = Goal(
            goal_id=f"goal_{uuid.uuid4().hex[:6]}",
            user_id=user_id,
            objective=objective,
            success_criteria=success_criteria,
            priority=priority,
            state="active",
            self_correction_weight=sc_weight,
            is_long_horizon=is_long
        )
        
        # 5. Persistent SQL Storage (v13.0 Monolith)
        await self._persist_goal(goal)
            
        return goal

    async def _persist_goal(self, goal: Goal):
        """Saves goal to Postgres for long-horizon tracking."""
        try:
            from backend.db.postgres_db import get_write_session
            async with get_write_session() as session:
                # v13.0 Atomic SQL Persistence
                from sqlalchemy import text
                await session.execute(
                    text("""
                        INSERT INTO goals (goal_id, user_id, objective, success_criteria, priority, state, self_correction_weight, is_long_horizon)
                        VALUES (:id, :uid, :obj, :criteria, :pri, :st, :scw, :ilh)
                        ON CONFLICT (goal_id) DO UPDATE SET
                        objective = EXCLUDED.objective,
                        success_criteria = EXCLUDED.success_criteria,
                        state = EXCLUDED.state,
                        updated_at = CURRENT_TIMESTAMP
                    """),
                    {
                        "id": goal.goal_id,
                        "uid": goal.user_id,
                        "obj": goal.objective,
                        "criteria": json.dumps(goal.success_criteria),
                        "pri": goal.priority,
                        "st": goal.state,
                        "scw": goal.self_correction_weight,
                        "ilh": goal.is_long_horizon
                    }
                )
                logger.info(f"[GoalEngine] Mission Objective PERSISTED: {goal.goal_id}")
        except Exception as e:
            logger.error(f"[GoalEngine] SQL Persistence failure: {e}")

    async def get_pending_goals(self, user_id: str) -> List[Goal]:
        """Retrieves active long-horizon goals for the user from SQL."""
        try:
            from backend.db.postgres_db import get_read_session
            async with get_read_session() as session:
                from sqlalchemy import text
                result = await session.execute(
                    text("SELECT * FROM goals WHERE user_id = :uid AND state = 'active'"),
                    {"uid": user_id}
                )
                return [Goal(**dict(row)) for row in result.mappings()]
        except Exception as e:
            logger.error(f"[GoalEngine] SQL Retrieval failure: {e}")
            return []

    async def _formulate_evolutionary_objective(self, user_input: str, intent_type: str, prototypes: List[str]) -> str:
        """Formulates mission with subtle evolutionary reveals."""
        base_obj = f"Sovereign OS v13.0 Mission: {user_input} [Intent: {intent_type.upper()}]"
        
        if prototypes:
            relevant_proto = next((p for p in prototypes if f"[{intent_type}]" in p), None)
            if relevant_proto:
                reveal = f" (Synthesizing learned reasoning pattern for {intent_type} missions)"
                return f"{base_obj}{reveal}"
                
        return base_obj

    def _generate_success_criteria(self, intent_type: str, complexity: int, fragility: float = 0.0) -> List[str]:
        """Generates criteria with fragility-based hardening."""
        criteria = [
            "Alignment: Logical consistency with user objective.",
            "Grounding: Factual accuracy and source relevance.",
            "Resonance: Cognitive style and tone alignment.",
            "DCN Resonance: Cross-cluster rule validation (v13.0)."
        ]
        
        # Domain-Specific extras (Logic-First Hardening)
        if intent_type == "search":
             criteria.append("Investigative Depth: Multi-vector source synthesis.")
        elif intent_type == "code":
             criteria.append("Syntactic Correctness: Sandbox-passed logic.")
             criteria.append("Logic-First: Code execution via Python REPL Engine confirmed.")
             if fragility > 0.5:
                 criteria.append("Verification: Mandatory multi-path cross-check (Fragility Mode).")
        
        if complexity >= 3 or fragility > 0.7:
             criteria.append("Cross-Engine Validation: Swarm-based consensus check.")
             
        return criteria

    def _calculate_priority(self, complexity: int, intent_type: str) -> str:
        if complexity >= 4 or intent_type in ["code", "document"]:
             return "high"
        return "medium" if complexity >= 2 else "low"
