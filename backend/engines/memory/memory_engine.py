import logging
from typing import Any, Dict, List, Optional
from backend.engines.base import EngineBase, EngineResult
from .vault import MemoryVault

logger = logging.getLogger(__name__)

class MemoryEngine(EngineBase):
    """
    Sovereign Persistent Memory Engine.
    Coordinates between short-term context and long-term user resonance.
    """
    
    def __init__(self):
        super().__init__("Memory")
        self.vault_registry = {}

    def _get_vault(self, user_id: str) -> MemoryVault:
        """Retrieves or initializes a vault for a specific user."""
        if user_id not in self.vault_registry:
            self.vault_registry[user_id] = MemoryVault(user_id)
        return self.vault_registry[user_id]

    async def _run(self, user_id: str, query: str = "", action: str = "retrieve", **kwargs) -> Any:
        """
        Memory logic for storage and retrieval.
        """
        vault = self._get_vault(user_id)
        
        if action == "store":
            self.logger.info(f"Storing memory for {user_id}")
            content = kwargs.get("content", query)
            embedding = kwargs.get("embedding", [0.0]*384) # Placeholder
            metadata = kwargs.get("metadata", {})
            await vault.store(content, embedding, metadata)
            return {"status": "memory_engrained", "user_id": user_id}
            
        elif action == "retrieve":
            self.logger.info(f"Recalling memory for {user_id}")
            embedding = kwargs.get("embedding", [0.0]*384) # Placeholder
            results = await vault.recall_semantic(embedding, top_k=kwargs.get("top_k", 5))
            
            # Combine with LTM traits (Traits from static lookup for now)
            ltm = {"traits": ["analytical", "stoic"], "preferences": ["short-answers"]}
            
            return {
                "semantic": results,
                "traits": ltm["traits"],
                "preferences": ltm["preferences"],
                "summary": self._summarize_results(results)
            }
            
        return {"error": "Invalid memory action."}

    def _summarize_results(self, results: List[Dict]) -> str:
        """Heuristically summarizes memory hits into context strings."""
        if not results: return "No prior resonance found."
        
        summaries = [f"On {r.get('timestamp','unknown')}: {r.get('content','...')[:100]}" for r in results]
        return "Previously: " + " | ".join(summaries)
