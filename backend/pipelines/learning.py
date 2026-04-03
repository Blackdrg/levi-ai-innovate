import os
import logging
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.db.firestore_db import db as firestore_db

logger = logging.getLogger(__name__)

class LearningSystem:
    """
    Sovereign Self-Evolution Loop v8.
    Captures low-fidelity missions (failures) and maps them to prompt optimizations.
    """
    def __init__(self):
        self.failure_collection = firestore_db.collection("sovereign_failures")
        self.optimization_collection = firestore_db.collection("prompt_optimizations")

    async def log_failure(self, input_data: str, response: str, score: float, reasons: List[str]):
        """Persists a failed cognitive mission for future training/optimization."""
        failure_log = {
            "input": input_data,
            "response": response,
            "score": score,
            "reasons": reasons,
            "timestamp": datetime.now(timezone.utc),
            "optimized": False
        }
        try:
            self.failure_collection.add(failure_log)
            logger.info(f"[LearningSystem] Logged low-fidelity mission (Fidelity: {score:.2f})")
        except Exception as e:
            logger.error(f"[LearningSystem] Logging failure failed: {e}")

    async def improve(self):
        """
        Main optimization pass.
        Selects unoptimized failures, generates a 'Better Prompt', and updates the blueprint.
        """
        logger.info("[LearningSystem] Initiating self-improvement cycle...")
        
        # 1. Fetch unoptimized failures
        failures = self.failure_collection.where("optimized", "==", False).limit(10).stream()
        
        count = 0
        for doc in failures:
            data = doc.to_dict()
            
            # 2. Optimize prompt for this failure case
            improved_prompt = await self._optimize_prompt(data["input"], data["reasons"])
            
            # 3. Store optimization
            opt_id = self.optimization_collection.add({
                "original_input": data["input"],
                "improved_logic": improved_prompt,
                "applied": False,
                "source_failure": doc.id,
                "timestamp": datetime.now(timezone.utc)
            })[1].id
            
            # 4. Apply optimization (update blueprint)
            await self.update_prompt(improved_prompt)

            # 5. Mark as optimized
            doc.reference.update({"optimized": True})
            count += 1

        logger.info(f"[LearningSystem] Optimization cycle complete. {count} improvements staged.")
        return count

    async def update_prompt(self, new_prompt: str):
        """Persists the optimized meta-prompt to the Sovereign Blueprint (Firestore)."""
        logger.info("[LearningSystem] Applying prompt optimization to Sovereign Blueprint.")
        try:
            blueprint_ref = firestore_db.collection("config").document("cognitive_blueprint")
            blueprint_ref.set({
                "meta_prompt": new_prompt,
                "updated_at": datetime.now(timezone.utc),
                "version": f"v8_evo_{uuid.uuid4().hex[:4]}"
            }, merge=True)
            
            # Sync to environment for fast-access
            os.environ["LEVI_META_PROMPT"] = new_prompt
        except Exception as e:
            logger.error(f"[LearningSystem] Failed to update blueprint: {e}")

    async def _optimize_prompt(self, input_data: str, reasons: List[str]) -> str:
        """Uses high-fidelity LLM to generate a better prompt strategy."""
        from backend.engines.chat.generation import SovereignGenerator
        
        opt_prompt = (
            f"Failure Analysis:\nInput: {input_data}\nIssues detected: {', '.join(reasons)}\n\n"
            "Analyze the failure and suggest a refined system instruction or meta-prompt "
            "to ensure the next response is high-fidelity and addresses these issues."
        )
        
        generator = SovereignGenerator()
        return await generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Optimization Architect."},
            {"role": "user", "content": opt_prompt}
        ])

# Global instance
learning_system = LearningSystem()
