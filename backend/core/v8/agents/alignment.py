from typing import Any, Dict
from pydantic import BaseModel
from .base import BaseV8Agent
from backend.core.orchestrator_types import AgentResult
from backend.services.brain_service import brain_service

class AlignmentInput(BaseModel):
    proposition: str
    constraints: Dict[str, Any] = {}

class AlignmentAgentV8(BaseV8Agent[AlignmentInput]):
    """
    Phase 3.7: Alignment Agent.
    Ensures that mission outcomes and propositions align with safety and ethical constraints.
    """
    def __init__(self):
        super().__init__("Alignment")
        self.__capabilities__ = ["safety", "alignment", "v14_autonomous"]

    async def _execute_system(self, input_data: AlignmentInput, context: Dict[str, Any]) -> AgentResult[Any]:
        self.logger.info(f"Verifying alignment for proposition: {input_data.proposition[:50]}...")
        
        prompt = f"""
        You are the LEVI Alignment Officer. Verify if the following proposition aligns with safety and ethical guidelines.
        
        Proposition: {input_data.proposition}
        Constraints: {input_data.constraints}
        
        Output 'ALIGNED' or 'DEVIANT' with reasons.
        """
        
        response = await brain_service.call_local_llm(prompt)
        
        success = "ALIGNED" in response.upper()
        
        return AgentResult(
            success=True,
            message=response,
            data={"aligned": success},
            agent=self.name
        )
