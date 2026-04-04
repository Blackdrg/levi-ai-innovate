import json
import logging
import os
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

EVOLUTION_FILE = os.path.join(os.path.dirname(__file__), "evolution_engine.json")

class EvolutionEngine:
    """
    Evolution Engine (v8.15)
    Upgraded from Rules Engine. Learns repeated patterns and promotes them
    to deterministic rules to skip LLM processing.
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
        """Normalizes task description for pattern matching."""
        # Lowercase, strip, and remove extra whitespace
        normalized = task.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        # Remove common punctuation that doesn't change intent
        normalized = re.sub(r'[?.!,]', '', normalized)
        return normalized

    def learn(self, task: str, result: Any):
        """
        Learns from a task/result pair. 
        Promotes to 'promoted' if count >= 3.
        """
        key = self._normalize(task)

        if key not in self.rules:
            self.rules[key] = {
                "count": 1,
                "result": result,
                "promoted": False
            }
            logger.info(f"[EvolutionEngine] New pattern detected: {key[:30]}...")
        else:
            self.rules[key]["count"] += 1
            # Update result if it's high quality or for consistency
            self.rules[key]["result"] = result 
            
            if self.rules[key]["count"] >= 3 and not self.rules[key].get("promoted"):
                self.rules[key]["promoted"] = True
                logger.info(f"[EvolutionEngine] Pattern PROMOTED to rule: {key[:30]}...")

        self._save_rules()

    def apply(self, task: str) -> Optional[Any]:
        """
        Checks if a promoted rule exists for the given task.
        """
        key = self._normalize(task)

        if key in self.rules and self.rules[key].get("promoted"):
            logger.info(f"[EvolutionEngine] Rule match found for: {key[:30]}...")
            return self.rules[key]["result"]

        return None

    def get_stats(self) -> Dict[str, Any]:
        promoted_count = sum(1 for r in self.rules.values() if r.get("promoted"))
        return {
            "total_patterns": len(self.rules),
            "promoted_rules": promoted_count
        }
