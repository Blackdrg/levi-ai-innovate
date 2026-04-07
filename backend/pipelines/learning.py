"""
Sovereign Self-Evolution Pipeline v13.0.0.
Captures low-fidelity missions (failures) and maps them to prompt optimizations.
Synchronized with the Sovereign OS SQL Fabric.
"""

import os
import logging
import json
import uuid
from typing import List
from datetime import datetime, timezone
from sqlalchemy import text
from backend.db.postgres_db import get_read_session, get_write_session

logger = logging.getLogger(__name__)

class LearningSystem:
    """
    Sovereign Self-Evolution Loop v13.0.0.
    Deterministic pattern promotion for high-fidelity cognitive growth.
    """

    async def log_failure(self, input_data: str, response: str, score: float, reasons: List[str]):
        """
        Persists a low-fidelity mission to the Postgres SQL Fabric ('agent_insights').
        """
        try:
            async with get_write_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO agent_insights (insight_id, user_id, type, description, resonance_score)
                        VALUES (:id, :uid, 'FAILURE_ANALYSIS', :desc, :score)
                    """),
                    {
                        "id": f"fail_{uuid.uuid4().hex[:8]}",
                        "uid": "system", # Global evolution
                        "desc": json.dumps({
                            "input": input_data,
                            "response": response,
                            "reasons": reasons,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }),
                        "score": score
                    }
                )
            logger.info(f"[Learning-v14] Logged low-fidelity mission (Resonance: {score:.2f})")
        except Exception as e:
            logger.error(f"[Learning-v13] SQL failure logging failed: {e}")

    async def improve(self):
        """
        Main optimization pass for the Sovereign OS.
        Selects failure insights, generates a SQL-backed 'System Patch', and updates the blueprint.
        """
        logger.info("[Learning-v13] Initiating self-improvement cycle...")
        
        # 1. Fetch unoptimized failures from agent_insights
        try:
            async with get_read_session() as session:
                res = await session.execute(
                    text("SELECT insight_id, description, resonance_score FROM agent_insights WHERE type = 'FAILURE_ANALYSIS' LIMIT 10")
                )
                failures = res.mappings().all()
        except Exception as e:
            logger.error(f"[Learning-v13] SQL fetch failed: {e}")
            return 0
        
        count = 0
        for data in failures:
            content = json.loads(data["description"])
            
            # 2. Optimize prompt for this failure case
            improved_prompt = await self._optimize_prompt(content["input"], content["reasons"])
            
            # 3. Store optimization in system_patches
            try:
                async with get_write_session() as session:
                    await session.execute(
                        text("""
                            INSERT INTO system_patches (domain, strategy, risk_score, confidence, status)
                            VALUES ('cognitive_blueprint', :strategy, :risk, :conf, 'applied_autonomous')
                        """),
                        {
                            "strategy": improved_prompt,
                            "risk": 0.1, # Initial autonomous risk calibration
                            "conf": 0.95
                        }
                    )
                
                # 4. Synchronize memory-blueprint (Fast-access)
                os.environ["LEVI_META_PROMPT"] = improved_prompt
                count += 1
            except Exception as e:
                logger.error(f"[Learning-v13] SQL patch persistence failed: {e}")

        logger.info(f"[Learning-v13] Optimization cycle complete. {count} patches crystallized.")
        return count

    async def _optimize_prompt(self, input_data: str, reasons: List[str]) -> str:
        """Uses the high-fidelity v13 Council of Models to generate optimization strategies."""
        from backend.engines.chat.generation import SovereignGenerator
        
        opt_prompt = (
            f"Failure Analysis (v13.0.0 Monolith):\nInput: {input_data}\nIssues: {', '.join(reasons)}\n\n"
            "Task: Refine the system-wide meta-prompt to prevent this neural drift."
        )
        
        generator = SovereignGenerator()
        return await generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Sovereign OS Optimization Architect."},
            {"role": "user", "content": opt_prompt}
        ])

# Global instance
learning_system = LearningSystem()

# Global instance
learning_system = LearningSystem()
