import logging
import json
import asyncio
from typing import List, Dict, Any
from sqlalchemy import select, insert, desc
from backend.db.postgres import PostgresDB
from backend.db.models import TrainingPattern

logger = logging.getLogger(__name__)

class LearningLoop:
    """
    Sovereign v1.0.0-RC1: Pattern Crystallization Engine.
    
    Captures high-fidelity mission results (Score > 0.85) and stores them 
    in the training_corpus for future model fine-tuning (LoRA / RLHF).
    Does NOT modify live model weights in the v1.0 release branch.
    """
    
    FIDELITY_THRESHOLD = 0.85
    ENABLED = True

    @classmethod
    async def crystallize_pattern(cls, mission_id: str, query: str, result: str, fidelity: float):
        """
        Stores mission results in the training ledger if they exceed the 
        fidelity threshold, ensuring only high-quality data is used for learning.
        """
        if not cls.ENABLED or fidelity < cls.FIDELITY_THRESHOLD:
            return

        try:
            async with PostgresDB._session_factory() as session:
                async with session.begin():
                    # Upsert logic to prevent duplicate missions
                    stmt = insert(TrainingPattern).values(
                        mission_id=mission_id,
                        query=query,
                        result=result,
                        fidelity_score=fidelity
                    ).on_conflict_do_nothing(index_elements=['mission_id'])
                    
                    await session.execute(stmt)
                await session.commit()
            logger.info(f"[LearningLoop] Crystallized pattern for mission: {mission_id} (S={fidelity:.2f})")
        except Exception as e:
            logger.error(f"[LearningLoop] Failed to crystallize pattern: {e}")

    @classmethod
    async def export_for_finetuning(cls, output_path: str, limit: int = 1000):
        """
        Exports the high-fidelity training corpus to JSONL format for LoRA fine-tuning.
        """
        logger.info(f"[LearningLoop] Exporting top {limit} patterns to {output_path}...")
        try:
            async with PostgresDB._session_factory() as session:
                stmt = select(TrainingPattern).order_by(desc(TrainingPattern.fidelity_score)).limit(limit)
                result = await session.execute(stmt)
                patterns = result.scalars().all()
                
                with open(output_path, "w") as f:
                    for p in patterns:
                        f.write(json.dumps({
                            "instruction": p.query,
                            "output": p.result,
                            "metadata": {
                                "mission_id": p.mission_id,
                                "fidelity": p.fidelity_score
                            }
                        }) + "\n")
            logger.info(f"[LearningLoop] Export complete: {len(patterns)} patterns.")
        except Exception as e:
            logger.error(f"[LearningLoop] Export failed: {e}")
