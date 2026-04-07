import os
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from backend.db.postgres_db import PostgresDB
from backend.db.models import TrainingPattern, user_facts # Use existing models
from backend.config.system import SOVEREIGN_VERSION

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/metrics")
async def get_learning_metrics():
    """
    Sovereign v13.1.0-Hardened-PROD Learning Dashboard API.
    Exposes real-time counts of the training corpus and knowledge base.
    """
    try:
        async with PostgresDB._session_factory() as session:
            # 1. Training Samples (Crystallized Patterns)
            samples_stmt = select(func.count()).select_from(TrainingPattern)
            samples_count = await session.execute(samples_stmt)
            
            # 2. Knowledge Base Entries (Episodic Facts)
            facts_stmt = select(func.count()).select_from(user_facts)
            facts_count = await session.execute(facts_stmt)
            
            return {
                "active_model": os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
                "training_samples": samples_count.scalar() or 0,
                "knowledge_base_entries": facts_count.scalar() or 0,
                "version": SOVEREIGN_VERSION,
                "status": "resonating"
            }
    except Exception as e:
        logger.error(f"[Learning API] Metrics sync failed: {e}")
        return {
            "active_model": "Unknown",
            "training_samples": 0,
            "knowledge_base_entries": 0,
            "status": "drifted"
        }
