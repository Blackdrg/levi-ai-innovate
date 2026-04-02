"""
backend/services/orchestrator/learning_escalation.py

The Fine-Tune Gatekeeper (Phase 4 Sovereignty).
Monitors system performance and manages the transition from 
In-Context Learning (ICL) to full Parameter-Efficient Fine-Tuning (PEFT).
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from backend.db.redis import r as redis_client, HAS_REDIS
from backend.services.learning.logic import get_learning_stats

logger = logging.getLogger(__name__)

# --- Escalation Thresholds ---
MIN_SAMPLES_FOR_FINETUNE = 500      # Don't even consider FT before 500 samples
QUALITY_DROP_THRESHOLD = 3.8       # Trigger FT if avg rating drops below this
FAILURE_THRESHOLD = 50             # Trigger FT if an agent fails > 50 times in a week
FT_COOLDOWN_DAYS = 7               # Don't re-train more than once a week

async def should_escalate_to_finetune() -> bool:
    """
    Analyzes system health and returns True if a fine-tuning job
    is economically and qualitatively justified.
    """
    if not HAS_REDIS:
        logger.warning("[Gatekeeper] Redis unavailable. Skipping escalation check.")
        return False

    try:
        # 1. Fetch current metrics
        stats = get_learning_stats()
        total_samples = stats.get("total_training_samples", 0)
        avg_rating = stats.get("avg_response_rating", 0.0)

        # 2. Check Sample Volume
        if total_samples < MIN_SAMPLES_FOR_FINETUNE:
            logger.info(f"[Gatekeeper] Volume too low for PEFT ({total_samples}/{MIN_SAMPLES_FOR_FINETUNE})")
            return False

        # 3. Check Quality Trend
        # If rating is high (>=4.0), the RAG/ICL system is working perfectly. No need to spend $$$ on FT.
        if avg_rating >= QUALITY_DROP_THRESHOLD:
            # Check for excessive agent failures as a secondary trigger
            from backend.db.redis_client import get_failure_count
            total_failures = get_failure_count("chat_agent") # Primary concern
            if total_failures < FAILURE_THRESHOLD:
                logger.info(f"[Gatekeeper] ICL performance is optimal (Rating: {avg_rating:.2f}, Failures: {total_failures}). PEFT postponed.")
                return False
            else:
                logger.warning(f"[Gatekeeper] QUALITY OK but FAILURE RATE HIGH ({total_failures}). ESCALATING TO PEFT.")
                return True

        # 4. Check Cooldown
        last_ft_time = redis_client.get("system:last_finetune_timestamp")
        if last_ft_time:
            last_dt = datetime.fromisoformat(last_ft_time.decode())
            if datetime.utcnow() - last_dt < timedelta(days=FT_COOLDOWN_DAYS):
                logger.info("[Gatekeeper] PEFT within cooldown period. Skipping.")
                return False

        # 5. Check explicitly if a job is already running
        from backend.services.orchestrator.fine_tune_tasks import get_active_ft_job
        active_job = await get_active_ft_job()
        if active_job:
            logger.info(f"[Gatekeeper] PEFT job {active_job} already in progress.")
            return False

        logger.warning(f"[Gatekeeper] CRITICAL: Quality drop detected ({avg_rating:.2f}). ESCALATING TO PEFT.")
        return True

    except Exception as e:
        logger.error(f"[Gatekeeper] Escalation analysis failed: {e}")
        return False

async def trigger_autonomous_finetune():
    """
    The 'Sovereign' Trigger: Evaluates and optionally kicks off a fine-tuning job.
    """
    if await should_escalate_to_finetune():
        try:
            from backend.services.orchestrator.fine_tune_tasks import start_finetune_pipeline
            job_id = await start_finetune_pipeline()
            if job_id:
                redis_client.set("system:last_finetune_timestamp", datetime.utcnow().isoformat())
                logger.info(f"[Gatekeeper] Sovereign FT Job Started: {job_id}")
                return job_id
        except Exception as e:
            logger.error(f"[Gatekeeper] Failed to start autonomous FT: {e}")
    
    return None
