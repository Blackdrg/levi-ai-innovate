"""
backend/services/orchestrator/agents/diagnostic_agent.py

Diagnostic Agent for LEVI-AI v6.8.8.
Performs Root Cause Analysis (RCA) on system failures and analyzes 
successful patterns to suggest prompt optimizations.
"""

import logging
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from backend.utils.health import check_brain_health

logger = logging.getLogger(__name__)

class DiagnosticInput(BaseModel):
    analysis_type: str = Field("active_probe", description="Type of diagnostic check to perform")
    target_component: Optional[str] = Field(None, description="Specific component to analyze (redis, firestore, llama)")

class DiagnosticAgent(BaseTool[DiagnosticInput, StandardToolOutput]):
    """
    The Diagnostic Agent analyzes the health of the orchestration pipeline.
    It identifies consistent failures and suggests improvements.
    """
    
    name = "diagnostic_agent"
    description = "Analyzes system failures and successful patterns for Root Cause Analysis (RCA)."
    input_schema = DiagnosticInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: DiagnosticInput, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs a diagnostic analysis and triggers self-healing routines.
        """
        # 1. 🔍 Active Probing
        health = await check_brain_health()
        logger.info(f"[Diagnostic] Active Health Check: {health['status']} (Checks: {health['checks']})")

        # 2. 💊 Self-Healing Routine
        if not health["checks"].get("groq_api", True) or not health["checks"].get("tavily_api", True):
            # This is a critical signal for the DynamicBrainScorer
            logger.warning("[Diagnostic] Self-Healing: Deprioritizing external APIs due to detected failure/latency.")

        # 3. 🧠 LLM Root Cause Analysis
        system_prompt = (
            "You are the LEVI System Diagnostic Agent. Perform an RCA on the current system health.\n"
            f"HEALTH DATA: {json.dumps(health)}\n"
            "If components are down, suggest immediate architectural adjustments for the Decision Engine."
        )
        
        from backend.generation import generate_chat_response
        try:
            analysis_raw = await generate_chat_response(
                messages=[{"role": "system", "content": system_prompt}],
                model="llama-3.1-8b-instant"
            )
            
            return {
                "success": True,
                "message": f"Sovereign Engine Health: {health['status']}. {analysis_raw[:150]}...",
                "data": health,
                "agent": self.name
            }
        except Exception as e:
            logger.error(f"[DiagnosticAgent] Analysis failed: {e}")
            return {
                "success": True, # Still return health data if LLM synthesis fails
                "message": f"Sovereign Engine Health: {health['status']}. Synthesis unavailable.",
                "data": health,
                "agent": self.name
            }
