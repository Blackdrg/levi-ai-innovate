# LEVI-AI Sovereign OS v22.0.0-GA: Autonomous Learning Loop
import asyncio
import logging
from typing import List
from datetime import datetime, timezone
from sqlalchemy import select, func, update
from backend.db.postgres import PostgresDB
from backend.db.models import GraduatedRule, Mission, MissionMetric
from backend.api.v8.telemetry import broadcast_mission_event

logger = logging.getLogger(__name__)

class LearningLoop:
    """
    Sovereign v22.0.0-GA: Intelligence Crystallization Engine.
    Monitors mission fidelity and promotes high-performance patterns to deterministic rules.
    """
    def __init__(self, pattern_threshold=0.96, min_uses=5):
        self.threshold = pattern_threshold
        self.min_uses = min_uses

    async def crystallize_pattern(self, mission_id: str, query: str, response: str, fidelity: float, signatures: List[str] = None):
        """
        Records a mission outcome and checks for rule crystallization potential.
        Sovereign v22-GA: Enforces BFT signature verification (Appendix G).
        """
        if fidelity < self.threshold: return 
        
        # Appendix G: Tier-4 BFT Verification
        if not signatures or len(signatures) < 1:
            logger.warning(f"⚠️ [LearningLoop] Rejected mission {mission_id}: NO BFT SIGNATURES.")
            return

        from backend.utils.kms import SovereignKMS
        valid_sigs = 0
        for sig in signatures:
            if await SovereignKMS.verify_trace(f"{mission_id}:{query}", sig):
                valid_sigs += 1
        
        if valid_sigs < 1:
             logger.error(f"🚨 [LearningLoop] BFT AUTHENTICATION FAILURE for mission {mission_id}.")
             return

        try:
            async with PostgresDB.session_scope() as session:
                # 1. Check for existing pattern
                stmt = select(GraduatedRule).where(GraduatedRule.task_pattern == query)
                result = await session.execute(stmt)
                rule = result.scalar_one_or_none()

                if rule:
                    # Update existing rule stats
                    rule.uses_count += 1
                    rule.fidelity_score = (rule.fidelity_score + fidelity) / 2
                    if rule.uses_count >= self.min_uses and rule.fidelity_score >= self.threshold:
                        rule.is_stable = True
                else:
                    # Create new candidate rule
                    new_rule = GraduatedRule(
                        task_pattern=query,
                        result_data={"response": response},
                        fidelity_score=fidelity,
                        uses_count=1,
                        is_stable=False
                    )
                    session.add(new_rule)
                
                logger.info(f"[LearningLoop] Crystallized pulse for mission {mission_id} (Fidelity: {fidelity})")
                broadcast_mission_event("system", "pattern_crystallized", {
                    "mission_id": mission_id,
                    "fidelity": fidelity,
                    "stable": rule.is_stable if rule else False
                })
        except Exception as e:
            logger.error(f"[LearningLoop] Crystallization failure: {e}")

    async def run_promotion_cycle(self):
        """
        Autonomous Cycle: Audits candidate rules and promotes stable ones.
        """
        logger.info("🌙 [LearningLoop] Initiating stability audit...")
        try:
            async with PostgresDB.session_scope() as session:
                stmt = update(GraduatedRule).where(
                    GraduatedRule.uses_count >= self.min_uses,
                    GraduatedRule.fidelity_score >= self.threshold,
                    GraduatedRule.is_stable == False
                ).values(is_stable=True, last_validated_at=datetime.now(timezone.utc))
                
                res = await session.execute(stmt)
                count = res.rowcount
                
                if count > 0:
                    logger.info(f"✅ [LearningLoop] Promoted {count} new deterministic rules to v22 Factual Ledger.")
        except Exception as e:
            logger.error(f"[LearningLoop] Promotion cycle failure: {e}")

    async def run_forever(self, interval_seconds=3600):
        """Main autonomous learning cycle."""
        logger.info(f"🧬 [LearningLoop] Autonomous pulse active (V22-GA)")
        while True:
            await self.run_promotion_cycle()
            await asyncio.sleep(interval_seconds)
