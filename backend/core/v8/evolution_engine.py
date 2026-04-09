"""
LEVI-AI Sovereign OS v14.0.0-Autonomous-SOVEREIGN [ACTIVE V14 COMPONENT].
Evolution Engine: Passive strategy culling and template drift optimization.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

EVOLUTION_FILE = os.path.join(os.path.dirname(__file__), "evolution_engine.json")

class EvolutionEngine:
    """
    Evolution Engine (v9.8)
    Sovereign Cognitive Optimization.
    Learns repeated patterns and promotes them to deterministic rules based on high-fidelity scores (>0.9).
    """

    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        if os.path.exists(EVOLUTION_FILE):
             try:
                 with open(EVOLUTION_FILE, "r") as f:
                     return json.load(f)
             except Exception as e:
                 logger.error(f"[EvolutionEngine] Failed to load rules: {e}")
        return {}

    def _save_rules(self):
        try:
            with open(EVOLUTION_FILE, "w") as f:
                json.dump(self.rules, f, indent=4)
        except Exception as e:
            logger.error(f"[EvolutionEngine] Failed to save rules: {e}")

    def _normalize(self, task: str) -> str:
        """Sovereign Normalization: Canonical intent representation."""
        normalized = task.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[?.!,]', '', normalized)
        return normalized

    def learn(self, task: str, result: Any, quality_score: float = 1.0):
        """
        LeviBrain v9.8: Qualitative Pattern Promotion.
        Learns from a task/result pair if the quality score meets the threshold.
        Promotes to 'promoted' if count >= 3 and average quality > 0.9.
        """
        key = self._normalize(task)

        if key not in self.rules:
            self.rules[key] = {
                "count": 1,
                "result": result,
                "avg_quality": quality_score,
                "promoted": False,
                "first_detected": datetime.now(timezone.utc).isoformat()
            }
            logger.info(f"[EvolutionEngine] New pattern detected: {key[:30]}...")
        else:
            data = self.rules[key]
            data["count"] += 1
            # Update running average quality
            data["avg_quality"] = (data["avg_quality"] * (data["count"] - 1) + quality_score) / data["count"]
            
            # Only update result if quality is better or equal
            if quality_score >= data.get("avg_quality", 0):
                data["result"] = result 
            
            # PROMOTION CRITERIA: Frequency (>2) and Fidelity (>0.9)
            if data["count"] >= 3 and data["avg_quality"] >= 0.9 and not data.get("promoted"):
                data["promoted"] = True
                data["promoted_at"] = datetime.now(timezone.utc).isoformat()
                logger.info(f"[EvolutionEngine] Pattern PROMOTED to Sovereign Rule: {key[:30]} (Fidelity: {data['avg_quality']:.2f})")
                
                # Check for autonomous transition to Neural Weights
                self.check_evolution_threshold()

        self._save_rules()

    def check_evolution_threshold(self):
        """
        Sovereign v9.8.1: Autonomous Transition.
        Transforms Deterministic Rules into Neural Weights via Together AI fine-tuning.
        """
        promoted_count = sum(1 for r in self.rules.values() if r.get("promoted"))
        threshold = int(os.getenv("EVOLUTION_FT_THRESHOLD", 20))
        
        if promoted_count >= threshold:
            logger.info(f"[Evolution] Threshold reached ({promoted_count}/{threshold}). Triggering Autonomous Fine-tuning...")
            try:
                # In a real system, we'd export the rules to a JSONL first.
                # For Phase 5, we trigger the automation pulse.
                from backend.utils.runtime_tasks import create_tracked_task
                create_tracked_task(self._async_trigger_ft(), name="evolution-ft-trigger")
            except Exception as e:
                logger.error(f"[Evolution] Failed to trigger FT: {e}")

    async def _async_trigger_ft(self):
        """Background worker for FT submission."""
        from backend.services.learning.trainer import submit_finetuning_job, upload_training_file
        # 1. Export rules to temporary training file
        temp_file = "/tmp/evolution_training.jsonl"
        with open(temp_file, "w") as f:
            for key, data in self.rules.items():
                if data.get("promoted"):
                    line = {"messages": [
                        {"role": "system", "content": "You are LEVI, a philosophical AI."},
                        {"role": "user", "content": key},
                        {"role": "assistant", "content": data["result"]}
                    ]}
                    f.write(json.dumps(line) + "\n")
        
        # 2. Upload and Submit
        file_id = upload_training_file(temp_file)
        if file_id:
            submit_finetuning_job(file_id, suffix=f"monolith_v{datetime.now().strftime('%m%d')}")
            logger.info("[Evolution] Autonomous FT Job submitted successfully.")

    def apply(self, task: str) -> Optional[Any]:
        """
        Checks if a promoted Sovereign Rule exists for the given task.
        """
        key = self._normalize(task)
        if key in self.rules and self.rules[key].get("promoted"):
            logger.info(f"[EvolutionEngine] Deterministic Rule Match: {key[:30]}...")
            return self.rules[key]["result"]
        return None

    def get_stats(self) -> Dict[str, Any]:
        promoted_count = sum(1 for r in self.rules.values() if r.get("promoted"))
        return {
            "total_patterns": len(self.rules),
            "promoted_rules": promoted_count,
            "system_version": "9.8-Sovereign"
        }
