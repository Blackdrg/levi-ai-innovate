import logging
import asyncio
from typing import List, Dict, Any
from backend.core.replay_engine import ReplayEngine
from backend.utils.llm_utils import call_lightweight_llm

logger = logging.getLogger(__name__)

class ShadowTestSuite:
    """
    Sovereign Shadow Testing Framework v14.1.0.
    Re-runs historical missions using mutated configs to detect regressions.
    """
    def __init__(self):
        self.replay_engine = ReplayEngine()

    async def run_shadow_validation(self, old_prompt: str, new_prompt: str, mission_count: int = 5) -> bool:
        """
        Executes a shadow testing pass.
        Returns False if significant regression is detected.
        """
        logger.info(f"📊 [ShadowTest] Initiating pass on {mission_count} missions...")
        
        # 1. Fetch recent high-quality mission IDs from Firestore
        from backend.db.firebase import db
        docs = db.collection("training_data").where("rating", ">=", 4).order_by("created_at", direction="DESCENDING").limit(mission_count).get()
        mission_samples = [d.to_dict() for d in docs]
        
        if not mission_samples:
            logger.warning("[ShadowTest] No historical missions found for shadow testing.")
            return True # Assume safe if no data to prove otherwise

        regressions = 0
        for sample in mission_samples:
            # 2. Re-run mission with NEW prompt (Simulated context)
            user_input = sample.get("user_message")
            original_response = sample.get("bot_response")
            
            # Simple simulation: Call LLM with the new prompt vs old prompt's result
            # In a full impl, we'd use ReplayEngine to re-trace the entire DAG.
            try:
                shadow_res = await call_lightweight_llm([
                    {"role": "system", "content": new_prompt},
                    {"role": "user", "content": user_input}
                ])
                
                # 3. Semantic Comparison (Qualitative)
                similarity = await self._compare_responses(original_response, shadow_res, user_input)
                
                if similarity < 0.7:
                    logger.warning(f"[ShadowTest] Regression detected! Similarity: {similarity:.2f}")
                    regressions += 1
            except Exception as e:
                logger.error(f"[ShadowTest] Loop error: {e}")
                regressions += 1

        # Failure threshold: If > 40% of missions regress, reject mutation
        failure_rate = regressions / len(mission_samples)
        logger.info(f"📊 [ShadowTest] Pass complete. Regression rate: {failure_rate*100:.1f}%")
        
        return failure_rate < 0.4

    async def _compare_responses(self, original: str, shadow: str, goal: str) -> float:
        """Uses a judge LLM to compare original vs shadow fidelity."""
        judge_prompt = f"""
        Compare two AI responses to the same input.
        Input: {goal}
        Original: {original}
        Shadow: {shadow}
        
        Rate the Semantic Alignment and Fidelity of the Shadow response to the Original on a scale of 0.0 to 1.0.
        Output ONLY the float value.
        """
        try:
            res = await call_lightweight_llm([{"role": "system", "content": judge_prompt}])
            return float(res.strip())
        except:
            return 0.5 # Default to neutral if judge fails
