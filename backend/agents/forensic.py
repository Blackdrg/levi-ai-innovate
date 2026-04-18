# backend/agents/forensic.py
import logging
import json
import hashlib
from typing import Dict, Any, List, Optional
from backend.agents.base import BaseAgent, AgentInput, AgentOutput
from backend.utils.kms import SovereignKMS

logger = logging.getLogger(__name__)

class ForensicAgent(BaseAgent):
    """
    Sovereign Forensic: The Audit Authority.
    Performs forensic analysis of mission failures and verifies pulse integrity.
    """

    def __init__(self):
        super().__init__(
            agent_id="forensic_agent",
            name="Forensic",
            role="Audit & Trace Integrity",
            goal="Ensure absolute non-repudiability of system operations."
        )

    async def _run(self, input_data: AgentInput) -> AgentOutput:
        """Analyzes mission traces for anomalies or tampering."""
        objective = input_data.objective
        mission_id = input_data.context.get("mission_id", "unknown")
        
        logger.info(f"🔍 [Forensic] Analyzing mission trace for: {mission_id}")
        
        # 1. Fetch Trace
        from backend.services.audit_ledger import audit_ledger
        trace = await audit_ledger.get_trace(mission_id)
        
        if not trace:
            return AgentOutput(
                agent_id=self.agent_id,
                success=False,
                output="Audit trace not found. Integrity cannot be verified.",
                data={"error": "trace_missing"}
            )

        # 2. Verify Signatures
        valid = await self._verify_pulse_chain(trace)
        
        # 3. Graduation Compliance Check
        compliance = await self._check_graduation_compliance(trace)
        
        # 4. Analyze for Hallucinations or Bias
        from backend.utils.llm_utils import call_heavyweight_llm
        analysis_prompt = (
            "You are the LEVI Forensic Analyst. Review the following mission trace for:\n"
            "1. Logical inconsistencies.\n"
            "2. Potential security leaks (credentials, paths).\n"
            "3. Hallucination signals.\n\n"
            f"TRACE:\n{json.dumps(trace, indent=2)}\n\n"
            f"COMPLIANCE_ALERTS: {compliance}\n\n"
            "Provide a forensic verdict (SAFE | TAMPERED | ANOMALY)."
        )
        
        verdict = await call_heavyweight_llm([{"role": "user", "content": analysis_prompt}])
        
        return AgentOutput(
            agent_id=self.agent_id,
            success=valid and (not compliance),
            output=f"Forensic Analysis Complete. Status: {'VERIFIED' if valid else 'TAMPERED'}.\n\n{verdict}",
            data={
                "integrity_verdict": "VERIFIED" if valid else "TAMPERED",
                "detailed_analysis": verdict,
                "graduation_compliance": compliance,
                "trace_hash": hashlib.sha256(json.dumps(trace).encode()).hexdigest()
            }
        )

    async def _verify_pulse_chain(self, trace: List[Dict[str, Any]]) -> bool:
        """Verifies that every pulse in the chain is signed correctly."""
        for pulse in trace:
            sig = pulse.get("audit_sig")
            if not sig: return False
            # Verify via KMS
            if not await SovereignKMS.verify_trace(pulse, sig):
                return False
        return True

    async def _check_graduation_compliance(self, trace: List[Dict[str, Any]]) -> List[str]:
        """Ensures the mission followed v17.5 Graduation protocols."""
        alerts = []
        for pulse in trace:
            # Check for HAL-0 admission
            if not pulse.get("hal0_admitted"):
                alerts.append(f"VIOLATION: Pulse {pulse.get('step')} bypassed HAL-0 admission gate.")
            # Check for BFT signing
            if not pulse.get("bft_signed"):
                alerts.append(f"VIOLATION: Pulse {pulse.get('step')} missing hardware-level BFT signature.")
        return alerts
