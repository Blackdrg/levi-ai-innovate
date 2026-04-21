import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult

logger = logging.getLogger(__name__)

class SentinelInput(BaseModel):
    input: str = Field(..., description="The content to validate")

class SentinelAgent(SovereignAgent[SentinelInput, AgentResult]):
    """
    Sovereign Sentinel Agent.
    Role: Validate output and detect anomalies.
    """
    
    def __init__(self):
        super().__init__("Sentinel", profile="The Custodian")
        self.system_prompt_template = (
            "You are the LEVI Sentinel Agent.\n"
            "Mission: Validate the provided content for accuracy, security, and alignment.\n"
            "Output: Return 'VALID' if the content is correct and safe, otherwise return 'INVALID' followed by a brief reason."
        )

    async def _run(self, input_data: SentinelInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        content = input_data.input
        self.logger.info(f"Validating content: {content[:50]}")
        
        from backend.core.local_engine import handle_local_sync
        
        result = await handle_local_sync([
            {"role": "system", "content": self.system_prompt_template},
            {"role": "user", "content": content}
        ])
        
        return {
            "message": result,
            "data": {"agent": "sentinel", "valid": "VALID" in result.upper()}
        }
