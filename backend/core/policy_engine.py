"""
LEVI-AI v14.0 Brain Policy Engine.
The central decision core that converts intent and state into system-wide execution policy.
"""

import logging
from typing import Dict, Any, List, Optional
from .orchestrator_types import (
    BrainDecision, 
    BrainMode, 
    MemoryPolicy, 
    ExecutionPolicy, 
    LLMPolicy,
    IntentResult,
    IntentGraph
)

logger = logging.getLogger(__name__)

class BrainPolicyEngine:
    """
    v14.0 Brain Policy Engine.
    Implements Strategy Selection, Resource Allocation, and Execution Constraints.
    """

    def __init__(self):
        pass

    async def decide(
        self, 
        user_input: str, 
        intent: IntentResult, 
        intent_graph: Optional[IntentGraph] = None,
        security_context: str = "normal",
        **kwargs
    ) -> BrainDecision:
        """
        Main decision entry point.
        Calculates the BrainDecision based on hybrid heuristic + logic rules.
        """
        complexity = intent.complexity_level / 3.0 # Normalize to 0-1
        risk_level = 0.8 if intent.is_sensitive or security_context != "normal" else 0.1
        
        # 1. Mode Selection
        mode = self._select_mode(intent, complexity, risk_level)
        
        # 2. Resource Allocation Policy
        enable_agents = self._allocate_agents(mode, intent, complexity)
        memory_policy = self._allocate_memory(mode, intent)
        
        # 3. Execution Policy
        execution_policy = self._define_execution_policy(mode, complexity)
        
        # 4. LLM Policy
        llm_policy = self._define_llm_policy(mode, risk_level)
        
        decision = BrainDecision(
            mode=mode,
            enable_agents=enable_agents,
            memory_policy=memory_policy,
            execution_policy=execution_policy,
            llm_policy=llm_policy,
            risk_level=risk_level,
            complexity_score=complexity
        )
        
        logger.info(f"[Brain Policy] Decision: Mode={mode}, Agents={enable_agents}")
        return decision

    def _select_mode(self, intent: IntentResult, complexity: float, risk_level: float) -> BrainMode:
        """Logic for selecting the cognitive mode."""
        if risk_level > 0.7:
            return BrainMode.SECURE
        
        if intent.intent_type == "search" or "research" in intent.intent_type:
            return BrainMode.RESEARCH
        
        if complexity > 0.7:
            return BrainMode.DEEP
        
        if complexity < 0.3:
            return BrainMode.FAST
            
        return BrainMode.BALANCED

    def _allocate_agents(self, mode: BrainMode, intent: IntentResult, complexity: float) -> Dict[str, bool]:
        """Decides which agents should be activated."""
        agents = {
            "planner": True,
            "critic": False,
            "retrieval": False,
            "browser": False,
            "docker": False
        }
        
        if mode == BrainMode.FAST:
            agents["planner"] = False # Fast path doesn't need a formal planner
            
        if mode in [BrainMode.DEEP, BrainMode.RESEARCH, BrainMode.SECURE]:
            agents["critic"] = True
            
        if mode == BrainMode.RESEARCH or intent.intent_type == "search":
            agents["retrieval"] = True
            agents["browser"] = True
            
        if intent.intent_type == "code" and mode != BrainMode.FAST:
            agents["docker"] = True
            
        return agents

    def _allocate_memory(self, mode: BrainMode, intent: IntentResult) -> MemoryPolicy:
        """Decides which memory tiers to activate."""
        policy = MemoryPolicy(
            redis=True, # Always on for runtime state
            postgres=True, # Always on for audit/history
            neo4j=False,
            faiss=True
        )
        
        if mode in [BrainMode.RESEARCH, BrainMode.DEEP]:
            policy.neo4j = True
            
        if intent.intent_type == "knowledge":
            policy.neo4j = True
            
        return policy

    def _define_execution_policy(self, mode: BrainMode, complexity: float) -> ExecutionPolicy:
        """Defines runtime execution constraints."""
        policy = ExecutionPolicy(
            parallel_waves=2,
            max_retries=1,
            sandbox_required=False
        )
        
        if complexity > 0.7:
            policy.parallel_waves = 4
            
        if complexity < 0.3:
            policy.parallel_waves = 1 # Sequential
            
        if mode == BrainMode.SECURE:
            policy.sandbox_required = True
            policy.max_retries = 0 # Fail fast in secure mode
            
        if mode == BrainMode.RESEARCH:
            policy.max_retries = 3 # Be more persistent in research
            
        return policy

    def _define_llm_policy(self, mode: BrainMode, risk_level: float) -> LLMPolicy:
        """Defines LLM routing policy."""
        policy = LLMPolicy(
            local_only=True,
            cloud_fallback=False
        )
        
        if mode == BrainMode.DEEP and risk_level < 0.5:
            policy.cloud_fallback = True # Allow cloud for deep reasoning if not high risk
            
        if mode == BrainMode.SECURE:
            policy.local_only = True
            policy.cloud_fallback = False # Hard isolation
            
        return policy
