import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from backend.core.agent_base import SovereignAgent, AgentResult
from backend.core.local_engine import handle_local_task

logger = logging.getLogger(__name__)

class LocalInput(BaseModel):
    input: str = Field(..., description="The user's query")
    complexity: int = 1

class LocalAgent(SovereignAgent[LocalInput, AgentResult]):
    """
    Sovereign Local Handler (LocalHandler).
    Privacy-first, zero-latency responder for simple tasks and orientation.
    """
    
    def __init__(self):
        super().__init__("LocalHandler")

    async def _run(self, input_data: LocalInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Local Response Protocol v7:
        1. Low-complexity GGUF Inference.
        2. Fallback Transition to Council Pulse if needed.
        """
        query = input_data.input
        self.logger.info(f"Local Mission: {query[:40]}")
        
        # Engage the local engine bridge
        # Directly calling the low-latency handle_local_task
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
