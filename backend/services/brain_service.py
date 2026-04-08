import os
import logging
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from backend.core.orchestrator_types import (
    BrainMode, 
    MemoryPolicy, 
    ExecutionPolicy, 
    LLMPolicy, 
    BrainDecision,
    IntentResult
)
from backend.core.policy_engine import BrainPolicyEngine
from backend.utils.decision_logger import DecisionLogger
from backend.broadcast_utils import SovereignBroadcaster

logger = logging.getLogger(__name__)

class DecisionScores(BaseModel):
    complexity_score: float = Field(0.0, ge=0.0, le=1.0)
    risk_score: float = Field(0.0, ge=0.0, le=1.0)
    tool_dependency_score: float = Field(0.0, ge=0.0, le=1.0)
    latency_budget_estimate: float = 500.0 # ms

class BrainPolicy(BaseModel):
    """
    Sovereign v14.0 Policy Object.
    The immutable contract for execution.
    """
    mode: str
    enable: Dict[str, bool]
    execution: Dict[str, Any]
    llm: Dict[str, Any]
    memory: Dict[str, bool]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    policy_id: str = Field(default_factory=lambda: f"pol_{uuid.uuid4().hex[:8]}")

class BrainService:
    """
    Sovereign Brain Decision Service v14.0.
    Centrally governs system behavior via policy generation.
    """
    
    def __init__(self):
        self.policy_engine = BrainPolicyEngine()
        # Internal Service Token for S2S Auth
        self.service_token = os.getenv("BRAIN_SERVICE_TOKEN", "sovereign_internal_pulse_v14")

    async def analyze_intent(self, query: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        """Deep intent classification wrapper."""
        from backend.core.perception import PerceptionEngine
        from backend.memory.manager import MemoryManager
        
        # We use a temporary memory manager for perception if not provided
        perception_engine = PerceptionEngine(MemoryManager())
        perception = await perception_engine.perceive(query, "system", "brain_service_analysis")
        return perception["intent"]

    async def compute_scores(self, query: str, intent: IntentResult) -> DecisionScores:
        """Computes granular scores for policy decision."""
        # Heuristic scoring for now (as requested in Step 2)
        complexity = intent.complexity_level / 3.0
        risk = 0.8 if intent.is_sensitive else 0.1
        
        # Tool dependency based on intent type
        tool_dep = 0.2
        if intent.intent_type in ["code", "search", "research", "visual"]:
            tool_dep = 0.8
            
        return DecisionScores(
            complexity_score=complexity,
            risk_score=risk,
            tool_dependency_score=tool_dep,
            latency_budget_estimate=1000.0 if complexity > 0.5 else 400.0
        )

    async def generate_policy(self, query: str, context: Optional[Dict[str, Any]] = None) -> BrainPolicy:
        """
        Master policy generation pipeline.
        Calculates scores -> Decides Mode -> Generates Policy Object.
        """
        # 1. Analyze Intent
        intent = await self.analyze_intent(query, context)
        
        # 2. Compute Scores
        scores = await self.compute_scores(query, intent)
        
        # 3. Use Policy Engine for internal logic
        decision: BrainDecision = await self.policy_engine.decide(
            user_input=query,
            intent=intent,
            security_context="high" if scores.risk_score > 0.5 else "normal"
        )
        
        # 4. Map to requested Policy Object structure
        policy = BrainPolicy(
            mode=decision.mode.value,
            enable={
                **decision.enable_agents,
                "sandbox": decision.execution_policy.sandbox_required,
            },
            execution={
                "parallel_waves": decision.execution_policy.parallel_waves,
                "max_retries": decision.execution_policy.max_retries,
                "retry_strategy": decision.execution_policy.retry_strategy,
                "budget": decision.execution_policy.budget.model_dump(),
            },
            llm={
                "local_only": decision.llm_policy.local_only,
                "fallback_allowed": decision.llm_policy.cloud_fallback
            },
            memory={
                "redis": decision.memory_policy.redis,
                "postgres": decision.memory_policy.postgres,
                "neo4j": decision.memory_policy.neo4j,
                "faiss": decision.memory_policy.faiss,
            }
        )
        # 5. Log decision trace (v14.0)
        await DecisionLogger.log_decision(
            request_id=(context or {}).get("request_id", f"gen_{uuid.uuid4().hex[:8]}"),
            query=query,
            scores=scores.model_dump(),
            policy=policy.model_dump()
        )
        
        # 6. Broadcast Neural Pulse (Real-time Telemetry)
        SovereignBroadcaster.publish("BRAIN_POLICY_LOCKED", {
            "policy_id": policy.policy_id,
            "mode": policy.mode,
            "complexity": scores.complexity_score,
            "risk": scores.risk_score,
            "enable": policy.enable
        }, user_id=(context or {}).get("user_id", "global"))
        
        logger.info(f"[BrainService] Policy generated: {policy.policy_id} Mode: {policy.mode}")
        return policy

    def verify_service_token(self, token: str) -> bool:
        """Validates internal service-to-service token."""
        return token == self.service_token

brain_service = BrainService()
