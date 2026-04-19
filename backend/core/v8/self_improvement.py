import logging
import asyncio
from typing import Dict, Any

from .learning import LearningLoopV8, FragilityTracker
from backend.pipelines.learning import learning_system
from backend.api.v8.telemetry import broadcast_mission_event
from backend.services.analytics import record_mission_metrics

logger = logging.getLogger(__name__)

class SelfImprovementLoop:
    """
    LeviBrain v8.14: Self-Improvement Loop.
    The autonomous brain layer that bridges real-time learning with long-term optimization.
    """

    @classmethod
    async def process_mission(cls, user_id: str, outcome: Dict[str, Any]):
        """
        Processes a mission outcome and triggers the appropriate learning response.
        - Success (Recurring) -> Rule Promotion (LearningLoopV8)
        - Success (Extreme) -> Crystallization (LearningLoopV8)
        - Failure -> LoRA Training Data & Prompt Optimization (LearningSystem)
        """
        success = outcome.get("success", False)
        intent = outcome.get("intent", "general")
        score = outcome.get("score", 1.0) if success else 0.0
        
        logger.info(f"[SelfImprovement] Processing mission outcome: Success={success}, Intent={intent}")

        # 1. Real-time In-Memory Learning (v8.12 logic)
        # This handles Rule Promotion and Fragility tracking
        await LearningLoopV8.process_mission_outcome(user_id, outcome)

        # 1.5. Sovereign Persistence: Postgres Analytics (v13.0)
        from backend.utils.runtime_tasks import create_tracked_task
        create_tracked_task(record_mission_metrics(user_id, outcome), name="record_mission_metrics")

        # 2. Long-term Structural Optimization (v8.14 logic)
        if not success:
            # Failure Analysis -> Log for LLM-based Prompt Optimization
            reasons = outcome.get("reasons", ["Logic Divergence"])
            await learning_system.log_failure(
                input_data=outcome.get("query", ""),
                response=outcome.get("response", ""),
                score=score,
                reasons=reasons
            )
            
            # Broadcast Evolution Event
            broadcast_mission_event(user_id, "self_improvement_logged", {
                "intent": intent,
                "type": "failure_optimization",
                "fragility": FragilityTracker.get_fragility(user_id, intent)
            })
        else:
            # Success -> Potential for Wisdom Scraping (EvolutionEngine)
            if score >= 0.95:
                # v8.14 Wisdom Crystallization: Promote high-fidelity results to Tier 2
                from backend.services.memory_manager import MemoryManager
                memory = MemoryManager()
                await memory.crystallize_fact(user_id, {
                    "content": outcome.get("response", ""),
                    "intent": intent,
                    "fidelity": score,
                    "source": "autonomous_improvement"
                })
                logger.info(f"[SelfImprovement] Wisdom crystallized for {user_id} (Fidelity: {score:.2f})")

    @classmethod
    async def run_optimization_cycle(cls):
        """
        Background task to perform batch optimization of internal prompts.
        This closes the loop by applying learned improvements to the Blueprint.
        """
        logger.info("[SelfImprovement] Starting autonomous optimization cycle...")
        try:
            # This calls the Firestore-based learning system to optimize prompts
            count = await learning_system.improve()
            logger.info(f"[SelfImprovement] Optimization cycle complete. Applied {count} improvements.")
            return count
        except Exception as e:
            logger.error(f"[SelfImprovement] Optimization cycle failed: {e}")
            return 0
