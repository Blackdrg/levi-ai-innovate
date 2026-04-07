# learning_loop.py — simplified but working version (v13.0)
import asyncio
import logging

logger = logging.getLogger(__name__)

class LearningLoop:
    def __init__(self, db_pool, pattern_threshold=0.95, min_uses=3):
        self.db = db_pool
        self.threshold = pattern_threshold
        self.min_uses = min_uses

    async def record_pattern(self, pattern_hash: str, dag_structure: dict, score: float):
        """Records a successful execution pattern for potential promotion."""
        try:
            await self.db.execute("""
                INSERT INTO intelligence_traits (trait_id, pattern, significance, usage_count)
                VALUES ($1, $2, $3, 1)
                ON CONFLICT (trait_id) DO UPDATE
                SET usage_count = intelligence_traits.usage_count + 1,
                    significance = ($3 + intelligence_traits.significance) / 2,
                    last_used = NOW()
            """, pattern_hash, str(dag_structure), score)
            logger.info(f"[LearningLoop] Pattern recorded: {pattern_hash}")
        except Exception as e:
            logger.error(f"[LearningLoop] Failed to record pattern: {e}")

    async def promote_patterns(self):
        """Runs on schedule — promotes high-fidelity patterns to Level 1 rules."""
        try:
            rows = await self.db.fetch("""
                SELECT trait_id, pattern, significance, usage_count
                FROM intelligence_traits
                WHERE significance >= $1 
                AND usage_count >= $2
                AND promoted = FALSE
            """, self.threshold, self.min_uses)

            for row in rows:
                logger.info(f"[PROMOTING] Pattern {row['trait_id']} → Level 1 Rule")
                await self.db.execute("""
                    UPDATE intelligence_traits 
                    SET promoted = TRUE 
                    WHERE trait_id = $1
                """, row['trait_id'])
        except Exception as e:
            logger.error(f"[LearningLoop] Promotion cycle failure: {e}")

    async def run_forever(self, interval_seconds=3600):
        """Main autonomous learning cycle."""
        logger.info(f"[LearningLoop] Autonomous pulse active (Interval: {interval_seconds}s)")
        while True:
            await self.promote_patterns()
            await asyncio.sleep(interval_seconds)
