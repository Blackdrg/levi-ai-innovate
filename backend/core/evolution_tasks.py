"""
LEVI-AI Sovereign OS v14.0.0-Autonomous-SOVEREIGN [ACTIVE V14 COMPONENT].
Evolution Tasks: Autonomous logic for the Weekly Global Evolution Cycle (The Dreaming Loop).
"""

import logging
import asyncio
from datetime import datetime
from sqlalchemy import text
from backend.celery_app import celery_app
from backend.core.v8.learning import PatternRegistry
from backend.core.v8.rules_engine import RulesEngine
from backend.core.v8.critic import ReflectionEngine
from backend.core.v8.sync_engine import SovereignSync
from backend.services.learning.trainer import export_training_data, upload_training_file, submit_finetuning_job

logger = logging.getLogger(__name__)

class WeeklyEvolution:
    """
    Sovereign Evolution Controller.
    Architectural bridge for triggering the Global Evolution Cycle (The Dreaming Loop).
    """
    async def run_weekly_evolution(self):
        """Initializes the weekly cognitive evolution logic."""
        logger.info("[WeeklyEvolution] Awakening the v13.0 Global Evolution Cycle...")
        await _execute_evolution_logic()
        return {"status": "success", "cycle": "weekly"}

@celery_app.task(name="run_weekly_evolution")
def run_weekly_evolution():
    """Executes the Weekly Global Evolution Cycle."""
    logger.info("[Evolution] Starting Global Evolution Cycle v13.0...")
    asyncio.run(_execute_evolution_logic())
    logger.info("[Evolution] Global Evolution Cycle COMPLETED.")

async def _execute_evolution_logic():
    """
    Internal core for v13.0 evolution logic.
    Performs Rule Promotion, Failure Clustering, and Recursive Patching.
    """
    rules_engine = RulesEngine()
    reflection_engine = ReflectionEngine()
    from backend.db.postgres_db import get_read_session, get_write_session
    
    # 1. Rule Promotion (SQL Pattern Distillation)
    try:
        async with get_read_session() as session:
            # Fetch high-fidelity missions from the last 7 days from SQL
            result = await session.execute(
                text("SELECT objective, status FROM missions WHERE status = 'completed' LIMIT 100")
            )
            for row in result.mappings():
                query = row["objective"]
                # Logic: If query has occurred multiple times, promote to rule
                if PatternRegistry.track_pattern("system", query, "N/A"):
                    logger.info(f"[Evolution] Distilling Rule: {query[:40]}...")
                    rules_engine.create_rule(query, "LEARNED_PATTERN_V13")

    except Exception as e:
        logger.error(f"[Evolution] Rule promotion cycle failed: {e}")

    # 2. Failure Cluster Analysis & SQL Recursive Patching
    try:
        async with get_read_session() as session:
            result = await session.execute(
                text("SELECT objective FROM missions WHERE status = 'failure' LIMIT 20")
            )
            failures = [{"query": row["objective"]} for row in result.mappings()]
            
            if failures:
                patch = await reflection_engine.suggest_system_patch(failures)
                risk = patch.get("risk_score", 1.0)
                confidence = patch.get("confidence", 0.0)
                
                async with get_write_session() as write_session:
                    status = "applied_autonomous" if risk < 0.2 and confidence > 0.9 else "pending_auditor"
                    await write_session.execute(
                        text("""
                            INSERT INTO system_patches (domain, strategy, risk_score, confidence, status)
                            VALUES (:domain, :strategy, :risk, :conf, :status)
                        """),
                        {
                            "domain": patch.get("domain", "general"),
                            "strategy": patch.get("strategy", ""),
                            "risk": risk,
                            "conf": confidence,
                            "status": status
                        }
                    )
                    logger.info(f"[Evolution] Sovereignty Patch ({status}) persisted to SQL.")

    except Exception as e:
        logger.error(f"[Evolution] failure analysis failed: {e}")

    # 3. Unbound Training Array Check (v13.0)
    try:
        output_path, count = await export_training_data()
        if count >= 100:
            logger.info(f"[Evolution] Threshold reached ({count}). Triggering Unbound Training Array.")
            file_id = upload_training_file(output_path)
            if file_id:
                submit_finetuning_job(file_id, suffix=f"levi_v13_{datetime.now().strftime('%m%d')}")
    except Exception as e:
        logger.error(f"[Evolution] Training cycle failed: {e}")

    # 4. Global DCN Synchronization (v13.0)
    try:
        await SovereignSync.sync_with_collective_hub()
    except Exception as e:
        logger.error(f"[Evolution] DCN Sync failed: {e}")

@celery_app.task(name="trigger_skill_crystallization")
def trigger_skill_crystallization(user_id: str, mission_id: str):
    """Event-driven skill acquisition (Prototype Layer)."""
    pass
