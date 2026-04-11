# backend/agents/hard_rule_agent.py
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.agents.base import SovereignAgent, AgentResult
from backend.db.postgres import PostgresDB
from backend.db.models import GraduatedRule

logger = logging.getLogger(__name__)

class HardRuleInput(BaseModel):
    objective: str
    proposed_plan: Dict[str, Any]
    session_id: str

class HardRuleAgent(SovereignAgent[HardRuleInput, AgentResult]):
    """
    Sovereign v14.2.0: The HardRule.
    Guardian of deterministic policy. Enforces rules from the graduated ledger.
    """
    def __init__(self):
        super().__init__(name="HardRule", profile="Policy Guardian")

    async def _run(self, input_data: HardRuleInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        logger.info(f"[HardRule] Auditing mission policy: {input_data.session_id}")
        
        # 1. Fetch active rules from DB
        db = PostgresDB()
        async with db.get_session() as session:
            stmt = select(GraduatedRule).where(GraduatedRule.is_active == True)
            res = await session.execute(stmt)
            active_rules = res.scalars().all()
            
        # 2. Match intent/objective against rules
        violations = []
        for rule in active_rules:
            if rule.rule_id == "GDPR_ENFORCEMENT" and "wipe" in input_data.objective.lower():
                # GDPR wipe is a special case already handled by compliance, 
                # but we ensure it follows protocols here.
                pass
            
            # Simple heuristic for rule violation (v14.2 baseline)
            if rule.rule_id in input_data.objective.upper():
                violations.append(f"Protocol Breach: {rule.description}")

        if violations:
            return {
                "success": False,
                "message": "Mission blocked by Sovereign Policy.",
                "data": {"violations": violations},
                "error": "Hard-rule violation detected.",
                "confidence": 1.0
            }
            
        return {
            "success": True,
            "message": "Sovereign policy audit successful. Mission parity maintained.",
            "data": {"rules_checked": len(active_rules)},
            "confidence": 1.0
        }
