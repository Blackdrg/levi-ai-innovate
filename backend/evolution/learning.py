import logging
from typing import Dict, Any, List
from backend.db.postgres import PostgresDB
from sqlalchemy import select, func

logger = logging.getLogger(__name__)

class SuccessLearner:
    """
    Sovereign Success Learner (Engine 7).
    Refines success patterns into deterministic rules.
    """
    def __init__(self):
        self.min_fidelity = 0.95

    async def distill_knowledge(self):
        """Processes high-fidelity traces into learning patterns."""
        logger.info("🧪 [SuccessLearner] Distilling knowledge from recent successes...")
        
        try:
            async with PostgresDB._session_factory() as session:
                from backend.db.models import SuccessPattern
                # Identify patterns with high fidelity and reoccurrence
                stmt = select(SuccessPattern).where(SuccessPattern.fidelity_avg >= self.min_fidelity)
                result = await session.execute(stmt)
                patterns = result.scalars().all()
                
                for pattern in patterns:
                    logger.info(f"✨ [SuccessLearner] Found stable pattern: {pattern.objective_pattern[:30]}")
                    # Transition to rule graduation logic
        except Exception as e:
            logger.error(f"[SuccessLearner] Learning cycle failed: {e}")

learner = SuccessLearner()
