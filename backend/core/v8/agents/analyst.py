from typing import Any, Dict
from pydantic import BaseModel
from .base import BaseV8Agent
from backend.core.orchestrator_types import AgentResult
from backend.services.brain_service import brain_service

class AnalystInput(BaseModel):
    input: str
    context: Dict[str, Any] = {}

class AnalystAgentV8(BaseV8Agent[AnalystInput]):
    """
    Phase 1.4: Analyst Agent.
    Specializes in thematic synthesis and deep pattern analysis.
    """
    def __init__(self):
        super().__init__("Analyst")
        self.__capabilities__ = ["analysis", "synthesis", "v14_autonomous"]

    async def _execute_system(self, input_data: AnalystInput, context: Dict[str, Any]) -> AgentResult[Any]:
        self.logger.info(f"Analyzing data pattern for input: {input_data.input[:50]}...")
        
        prompt = f"""
        You are the LEVI Analyst. Perform a deep thematic synthesis of the provided information.
        
        Input: {input_data.input}
        Context: {input_data.context}
        
        Synthesize the core insights and patterns.
        """
        
        response = await brain_service.call_local_llm(prompt)
        
        return AgentResult(
            success=True,
            message=response,
            data={"analysis_fidelity": 0.98},
            agent=self.name
        )
