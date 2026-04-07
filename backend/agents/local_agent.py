"""
Sovereign Local Agent v8.
Privacy-first, zero-latency responder for simple tasks.
Refactored into Autonomous Agent Ecosystem.
"""

import logging
from typing import Any, Dict
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult

logger = logging.getLogger(__name__)

class LocalInput(BaseModel):
    input: str = Field(..., description="The user's query")
    complexity: int = 1

class LocalAgent(SovereignAgent[LocalInput, AgentResult]):
    """
    Sovereign Local Handler.
    Zero-latency responder for low-complexity GGUF inference tasks.
    """
    
    def __init__(self):
        super().__init__("LocalHandler")

    async def _run(self, input_data: LocalInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Local Response Protocol v8:
        1. Low-complexity GGUF Inference.
        2. Escalation trigger if neural capacity exceeded.
        """
        query = input_data.input
        self.logger.info(f"Local Mission: {query[:40]}")
        
        # Engage the local engine bridge
        from backend.core.local_engine import handle_local_task
        response = await handle_local_task(query, complexity=input_data.complexity)
        
        if response == "FALLBACK":
             return {"message": "Mission exceeds local neural capacity. Escalating Pulse.", "success": False}
             
        return {
            "message": response,
            "data": {
                "local_resonance": True,
                "engine": "llama-cpp-gguf",
                "complexity_target": input_data.complexity
            }
        }
