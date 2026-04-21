import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult

logger = logging.getLogger(__name__)

class CognitionInput(BaseModel):
    input: str = Field(..., description="The context or task to reason about")

class CognitionAgent(SovereignAgent[CognitionInput, AgentResult]):
    """
    Sovereign Cognition Agent.
    Role: Generate reasoning and initial solutions.
    """
    
    def __init__(self):
        super().__init__("Cognition", profile="The Reasoner")
        self.system_prompt_template = (
            "You are the LEVI Cognition Agent.\n"
            "Mission: Provide deep reasoning and high-fidelity generation.\n"
            "Rules:\n"
            "1. Think step-by-step.\n"
            "2. Be concise but thorough.\n"
            "3. Focus on logical consistency."
        )

    async def _run(self, input_data: CognitionInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        task = input_data.input
        self.logger.info(f"Reasoning over mission: {task[:50]}")
        
        from backend.core.local_engine import handle_local_sync
        
        result = await handle_local_sync([
            {"role": "system", "content": self.system_prompt_template},
            {"role": "user", "content": task}
        ])
        
        return {
            "message": result,
            "data": {"agent": "cognition", "status": "processed"}
        }
