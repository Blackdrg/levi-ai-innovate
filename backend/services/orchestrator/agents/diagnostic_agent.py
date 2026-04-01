"""
backend/services/orchestrator/agents/diagnostic_agent.py

Diagnostic Agent for LEVI-AI (Phase 16).
Performs Root Cause Analysis (RCA) on system failures and analyzes 
successful patterns to suggest prompt optimizations.
"""

import logging
import json
from typing import Dict, Any
from ..tool_base import BaseTool
from ..orchestrator_types import ToolResult

logger = logging.getLogger(__name__)

class DiagnosticAgent(BaseTool):
    """
    The Diagnostic Agent analyzes the health of the orchestration pipeline.
    It identifies consistent failures and suggests improvements to 
    system prompts or fine-tuning requirements.
    """
    
    @property
    def name(self) -> str:
        return "diagnostic_agent"
    
    @property
    def description(self) -> str:
        return "Analyzes system failures and successful patterns for Root Cause Analysis (RCA)."

    async def _run(self, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """
        Runs a diagnostic analysis on the provided audit logs.
        """
        analysis_type = params.get("analysis_type", "failure_rca")
        audit_logs = params.get("audit_logs", [])
        success_samples = params.get("success_samples", [])
        
        if not audit_logs and not success_samples:
            return ToolResult(
                agent=self.name,
                success=False,
                error="No data provided for diagnostic analysis."
            )

        # 1. Build Diagnostic Prompt
        system_prompt = (
            "You are the LEVI System Diagnostic Agent. Your role is to perform Root Cause Analysis (RCA) "
            "on AI reasoning failures. You look for patterns in errors, intent mismatches, and hallucinations.\n"
            "Analyze the provided logs and identify the TOP 2 structural weaknesses in the current prompt/engine logic."
        )
        
        user_input = f"Analysis Type: {analysis_type}\n"
        if audit_logs:
            user_input += f"Failure Logs: {json.dumps(audit_logs[:5])}\n" # Sample only
        if success_samples:
            user_input += f"Success Patterns: {json.dumps(success_samples[:2])}\n"

        # 2. Call LLM for Diagnostic Reasoning
        from ..planner import call_lightweight_llm
        try:
            analysis_raw = await call_lightweight_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                model="llama-3.1-8b-instant"
            )
            
            # Simple parsing of recommendations
            recommendations = analysis_raw.strip()
            
            return ToolResult(
                agent=self.name,
                success=True,
                message=f"Diagnostic Analysis Complete: {recommendations[:200]}...",
                data={
                    "analysis": recommendations,
                    "type": analysis_type,
                    "confidence": 0.85
                },
                cost_score=0.1
            )
        except Exception as e:
            logger.error(f"[DiagnosticAgent] Analysis failed: {e}")
            return ToolResult(
                agent=self.name,
                success=False,
                error=str(e)
            )
