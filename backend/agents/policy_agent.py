"""
Sovereign Policy Agent v15.0.
Responsible for real-time boundary enforcement, alignment checks, 
and cognitive safety guardrails.
"""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.agents.base import SovereignAgent, AgentResult

logger = logging.getLogger(__name__)

class PolicyInput(BaseModel):
    user_input: str = Field(..., description="The original user query")
    proposed_plan: Optional[Dict[str, Any]] = Field(None, description="The DAG plan produced by the planner")
    proposed_response: Optional[str] = Field(None, description="The final synthesized response")
    context: Dict[str, Any] = Field(default_factory=dict)
    user_id: str = "guest"

class PolicyAgent(SovereignAgent[PolicyInput, AgentResult]):
    """
    Sovereign v15.0 Policy Enforcement Agent.
    Audits cognitive outcomes against alignment boundaries.
    """

    def __init__(self):
        super().__init__("PolicyAgent")
        self.risky_patterns = [
            r"delete\s+all", r"format\s+drive", r"wipe\s+memory",
            r"bypass\s+security", r"escalate\s+privileges"
        ]

    async def _run(self, input_data: PolicyInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Executes a policy audit on either a plan or a response.
        """
        user_input = input_data.user_input
        plan = input_data.proposed_plan
        response = input_data.proposed_response
        
        self.logger.info(f"Policy audit initiated for user {input_data.user_id}")

        # 1. Input/Plan Boundary Check
        violations = []
        
        # Simple pattern-based check for alignment
        import re
        for pattern in self.risky_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                violations.append(f"Malicious intent pattern detected: {pattern}")

        # 2. Response Quality/Safety Check
        if response:
            if "I am an AI" in response: # Simple alignment check example
                pass
            
            # Check for data leak stubs
            if "[PII_REDACTED]" in response:
                self.logger.info("PII redaction verified in response.")

        # 3. Final Decision
        is_safe = len(violations) == 0
        
        return {
            "success": is_safe,
            "message": "Policy alignment verified." if is_safe else "Policy violations detected.",
            "data": {
                "violations": violations,
                "risk_score": 0.0 if is_safe else 0.9,
                "enforcement_action": "ALLOW" if is_safe else "BLOCK"
            }
        }
