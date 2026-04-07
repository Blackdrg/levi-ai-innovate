import logging
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel
from backend.core.agent_base import SovereignAgent, AgentResult
from backend.engines.chat.generation import SovereignGenerator
from backend.utils.health import check_brain_health

logger = logging.getLogger(__name__)

class DiagnosticInput(BaseModel):
    analysis_type: str = "active_probe"
    target_component: Optional[str] = None

class DiagnosticAgent(SovereignAgent[DiagnosticInput, AgentResult]):
    """
    Sovereign System Diagnostic Agent (Diagnostic).
    Analyzes neural engine health and performs Root Cause Analysis.
    """
    
    def __init__(self):
        super().__init__("Diagnostic")

    async def _run(self, input_data: DiagnosticInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Diagnostic Protocol v7:
        1. Pulse Probing: Health check of active sub-services.
        2. Analysis: RCA of neural latency and failure patterns.
        3. Council-based Health Report.
        """
        self.logger.info("Initiating Neural Health Diagnostic Mission.")
        
        # Engage health monitoring utility
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

        return {
            "message": f"Neural Link Health: {status.upper()}.\n\n{analysis}",
            "data": {
                "health": health,
                "critical_anomalies": issues,
                "healing_status": "engaged" if issues else "nominal"
            }
        }
