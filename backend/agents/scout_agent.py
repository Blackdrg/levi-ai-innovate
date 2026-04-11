# backend/agents/scout_agent.py
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.agents.base import SovereignAgent, AgentResult

logger = logging.getLogger(__name__)

class ScoutInput(BaseModel):
    query: str
    deep_search: bool = False
    session_id: str

class ScoutAgent(SovereignAgent[ScoutInput, AgentResult]):
    """
    Sovereign v14.2.0: The Scout.
    Specialist in reconnaissance, discovery, and information gathering.
    """
    def __init__(self):
        super().__init__(name="Scout", profile="Reconnaissance Specialist")

    async def _run(self, input_data: ScoutInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        logger.info(f"[Scout] Discovery mission initiated: {input_data.query}")
        
        # 1. Memory Recon
        from backend.engines.memory.memory_engine import MemoryEngine
        memory = MemoryEngine()
        internal_context = await memory.execute(query=input_data.query, user_id=kwargs.get("user_id", "default"))
        
        # 2. External Recon
        from backend.engines.search.search_engine import SearchEngine
        search = SearchEngine()
        external_context = await search.search(input_data.query, deep=input_data.deep_search)
        
        # 3. Consolidation
        findings = {
            "internal": internal_context.get("data", []),
            "external": external_context.get("results", []),
            "total_signals": len(internal_context.get("data", [])) + len(external_context.get("results", []))
        }
        
        message = f"Scout mission successful. Detected {findings['total_signals']} relevant signals."
        
        return {
            "success": True,
            "message": message,
            "data": findings,
            "confidence": 0.95,
            "citations": [r.get("url") for r in findings["external"] if r.get("url")]
        }
