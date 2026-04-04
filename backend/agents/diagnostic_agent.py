"""
Sovereign Diagnostic Agent v8.
Analyzes neural engine health and performs Root Cause Analysis.
Refactored into Autonomous Agent Ecosystem.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class DiagnosticInput(BaseModel):
    analysis_type: str = "active_probe"
    target_component: Optional[str] = None

class DiagnosticAgent(SovereignAgent[DiagnosticInput, AgentResult]):
    """
    Sovereign System Diagnostic.
    Analyzes neural engine health and performs Root Cause Analysis.
    """
    
    def __init__(self):
        super().__init__("Diagnostic")

    async def _run(self, input_data: DiagnosticInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Diagnostic Protocol v8:
        1. Pulse Probing.
        2. RCA Analysis.
        3. Council-based Health Report.
        """
        self.logger.info("Initiating Neural Health Diagnostic Mission.")
        
        # Engage health monitoring utility
        from backend.utils.health import check_brain_health
        health = await check_brain_health()
        
        issues = [k for k, v in health.get("checks", {}).items() if not v]
        status = health.get("status", "unknown")
        
        system_prompt = (
            "You are the LEVI Sovereign Diagnostic Agent. Analyze the health pulse of the AI OS.\n"
            f"Current Metrics: {json.dumps(health)}\n"
            "Provide a concise Root Cause Analysis and recommended Sovereign mitigation if anomalies exist."
        )
        
        generator = SovereignGenerator()
        
        # Synthesize the health report using the Council
        analysis = await generator.council_of_models([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Analyze System Pulse."}
        ])

        # Phase 10: Sovereign OS Hard Hand (Self-Repair)
        if issues:
             await self._repair_system(issues)

        return {
            "message": f"Neural Link Health: {status.upper()}.\n\n{analysis}",
            "data": {
                "health": health,
                "critical_anomalies": issues,
                "healing_status": "engaged" if issues else "nominal",
                "repairs_attempted": issues
            }
        }

    async def _repair_system(self, issues: List[str]):
        """Phase 10: Sovereign OS Hard Hand (Self-Repair)."""
        for issue in issues:
            self.logger.info(f"[Diagnostic] Attempting Hard Hand repair for: {issue}")
            
            if "redis" in issue.lower():
                from backend.db.redis import r as redis_client, HAS_REDIS
                if HAS_REDIS:
                    # Clear failure queue to prevent cognitive bottlenecks
                    try:
                        redis_client.delete("sovereign:failure_queue")
                        self.logger.info("[Diagnostic] Purged Sovereign failure queue.")
                    except: pass
                    
            elif "vector" in issue.lower() or "faiss" in issue.lower():
                from backend.utils.vector_db import VectorDB
                # Reset all index instances to force a clean reload from disk (Recovery)
                VectorDB._instances = {}
                self.logger.info("[Diagnostic] Reset VectorDB global state for recovery.")
