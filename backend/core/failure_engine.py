"""
LEVI-AI v14.0 Failure Handling Engine.
Decides the Brain's recovery action based on specific failure types.
"""

import logging
from typing import Dict, Any, List, Optional
from .orchestrator_types import FailureType, FailureAction, BrainDecision

logger = logging.getLogger(__name__)

class FailurePolicyEngine:
    """
    v14.0 Failure Handling Layer.
    Implementation: retry -> compensate -> fallback -> abort.
    """

    async def determine_action(self, failure_type: FailureType, error: str, context: Dict[str, Any], decision: BrainDecision) -> FailureAction:
        """
        Main recovery logic based on v14.0 Brain Policy.
        """
        logger.info(f"[Failure Engine] Analyzing failure: {failure_type}. Error: {error[:100]}...")
        
        # 1. LLM Outage Recovery
        if failure_type == FailureType.LLM_ERROR:
            # Strategy: Primary -> Secondary -> Local
            if decision.llm_policy.cloud_fallback:
                logger.info("[Failure Engine] Activating Cloud Fallback Model.")
                return FailureAction(action="fallback", params={"model": "llama-3.1-8b-instant", "reason": "primary_llm_outage"})
            else:
                logger.warning("[Failure Engine] LLM Outage detected. No cloud fallback allowed. Aborting.")
                return FailureAction(action="abort", params={"reason": "llm_outage_no_fallback"})
        
        # 2. Tool Execution Failure
        if failure_type == FailureType.TOOL_FAILURE:
            retries = context.get("attempts", 0)
            max_retries = decision.execution_policy.max_retries
            
            if retries < max_retries:
                logger.info(f"[Failure Engine] Triggering Retry {retries+1}/{max_retries}")
                return FailureAction(action="retry", params={"delay": 2 ** retries})
            else:
                # Compensation Engine: Try an alternative path
                logger.warning("[Failure Engine] Max retries exhausted. Attempting Compensation strategy.")
                return FailureAction(action="compensate", params={
                    "strategy": "fallback_to_chat", 
                    "original_error": error
                })
        
        # 3. DAG Structure Conflict
        if failure_type == FailureType.DAG_CONFLICT:
            logger.error("[Failure Engine] Topological Conflict detected. Regenerating Plan.")
            return FailureAction(action="regenerate", params={"strategy": "shallow_dag"})
            
        # 4. Memory/Retrieval Mismatch
        if failure_type == FailureType.MEMORY_MISMATCH:
            logger.info("[Failure Engine] Memory Mismatch. Re-syncing retrieval context.")
            return FailureAction(action="resync", params={"tier": "retrieval"})
            
        return FailureAction(action="abort", params={"reason": "unhandled_anomaly"})
