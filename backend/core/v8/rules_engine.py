import json
import logging
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

RULES_FILE = os.path.join(os.path.dirname(__file__), "rules_engine.json")

class RulesEngine:
    """
    LeviBrain v8.12: Hardened Rules Engine.
    Manages persistent deterministic rules promoted from LLM reasoning patterns.
    """

    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        if os.path.exists(RULES_FILE):
             try:
                 with open(RULES_FILE, "r") as f:
                     return json.load(f)
             except Exception as e:
                 logger.error(f"[RulesEngine] Failed to load rules: {e}")
        return {"rules": {}}

    def _save_rules(self):
        try:
            with open(RULES_FILE, "w") as f:
                json.dump(self.rules, f, indent=4)
        except Exception as e:
            logger.error(f"[RulesEngine] Failed to save rules: {e}")

    async def get_rule(self, task_description: str, threshold: float = 0.95) -> Optional[str]:
        """
        Returns a cached solution if a deterministic rule exists.
        Supports both Exact Match and Fuzzy Vector Match (v8.14).
        """
        task_key = task_description.lower().strip()
        
        # 1. Exact Match (Fastest)
        exact_match = self.rules.get("rules", {}).get(task_key)
        if exact_match:
            logger.info(f"[RulesEngine] Exact rule match found for: {task_key[:30]}...")
            return exact_match

        # 2. Fuzzy Vector Match (v8.14)
        try:
            from backend.memory.vector_store import SovereignVectorStore
            # Search for rules in the vector store
            search_results = await SovereignVectorStore.search_memories(
                user_id="system_rules", # Rules are system-wide or user-specific? For now, system.
                query=task_description,
                limit=1,
                category="rule"
            )
            
            if search_results and search_results[0].get("score", 0) >= threshold:
                content = search_results[0]["content"]
                # Format: "Deterministic Rule: If input is '...', response is '...'"
                if "response is '" in content:
                    solution = content.split("response is '")[-1].rstrip("'")
                    logger.info(f"[RulesEngine] Fuzzy vector match found (Score: {search_results[0]['score']:.2f})")
                    return solution
        except Exception as e:
            logger.error(f"[RulesEngine] Fuzzy match failed: {e}")

        return None

    def create_rule(self, task_description: str, solution: str):
        """Persists a new deterministic rule locally and in vector store."""
        task_key = task_description.lower().strip()
        self.rules["rules"][task_key] = solution
        self._save_rules()
        
        # Async task to store in vector store (handled by caller or via asyncio)
        from backend.memory.vector_store import SovereignVectorStore
        import asyncio
        asyncio.create_task(SovereignVectorStore.store_fact(
            user_id="system_rules",
            fact=f"Deterministic Rule: If input is '{task_description}', response is '{solution}'",
            category="rule",
            importance=1.0
        ))
        
        logger.info(f"[RulesEngine] New rule created for: {task_key[:50]}...")

    def list_rules(self) -> Dict[str, str]:
        return self.rules.get("rules", {})
