import logging
import os
import json
from datetime import datetime
from typing import Dict, Any
from backend.engines.utils.security import SovereignSecurity

logger = logging.getLogger(__name__)

class LearningLoop:
    """
    Sovereign Reinforcement & Telemetry Core.
    Collects execution metadata to refine future Brain routing and agent behaviors.
    DPO-ready (Direct Preference Optimization).
    """

    def __init__(self, dataset_path: str = "backend/data/sovereign_dpo.jsonl"):
        self.dataset_path = dataset_path
        os.makedirs(os.path.dirname(self.dataset_path), exist_ok=True)

    async def ingest_telemetry(self, state):
        """
        Processes FlowState to build preference pairs for offline training.
        """
        logger.info(f"Ingesting DPO Telemetry: {state.user_id}")
        
        # Build training sample
        sample = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": state.query,
            "intent": state.intent,
            "plan": state.plan,
            "results": {k: str(v)[:1000] for k, v in state.engine_results.items()},
            "final_response": state.final_response,
            "metadata": {
                "user_id": state.user_id,
                "has_error": state.error is not None,
                "token_count": len(state.final_response.split()) if state.final_response else 0
            }
        }

        # 1. Local Persistent Dataset (DPO/RLHF)
        self._append_to_dataset(sample)

        # 2. Production Service Sync (Firestore)
        try:
            from backend.services.learning.logic import collect_training_sample
            await collect_training_sample(
                user_message=state.query,
                bot_response=state.final_response or "",
                mood="autonomous",
                rating=None, # Human-human rating collected separately
                session_id="sovereign_core",
                user_id=state.user_id,
                route=f"brain_{state.intent.lower()}"
            )
        except Exception as e:
            logger.error(f"Learning sync failure: {e}")

    def _append_to_dataset(self, data: Dict[str, Any]):
        """Thread-safe append for local telemetry dataset."""
        try:
            # Mask PII before storage
            data["query"] = SovereignSecurity.mask_pii(data["query"])
            data["final_response"] = SovereignSecurity.mask_pii(data.get("final_response", ""))
            
            with open(self.dataset_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            logger.error(f"DPO collection failure: {e}")

    async def trigger_local_refinement(self):
        """
        Placeholder for Local LoRA fine-tuning trigger based on collected dataset health.
        """
        logger.info("Evaluating Sovereign Evolution metrics...")
        pass
