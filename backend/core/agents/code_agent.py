"""
backend/services/orchestrator/agents/code_agent.py
"""

import logging
from typing import Any, Dict
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from backend.generation import _async_call_llm_api
from backend.payments import use_credits

logger = logging.getLogger(__name__)

class CodeInput(BaseModel):
    input: str = Field(..., description="The coding task or architectural query")
    user_id: str = "guest"
    user_tier: str = "free"

class CodeAgent(BaseTool[CodeInput, StandardToolOutput]):
    name = "code_agent"
    description = "Architect of logical and efficient structures."
    input_schema = CodeInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: CodeInput, context: Dict[str, Any]) -> Dict[str, Any]:
        # Credit Enforcement (Simplified for now)
        if input_data.user_id and not input_data.user_id.startswith("guest:"):
            try:
                use_credits(str(input_data.user_id), 2)
            except Exception as e:
                return {"success": False, "error": f"Insufficient credits: {str(e)}", "agent": self.name}

        system_prompt = (
            "You are the LEVI Architect. Generate clean, efficient, and well-documented code "
            "for the user's request. Include a brief architectural explanation. "
            "Use the requested language or Python by default."
        )
        
        response = await _async_call_llm_api(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Task: {input_data.input}"}
            ],
            model="llama-3.1-70b-versatile",
            provider="groq"
        )
        
        return {
            "success": True,
            "message": response or "I could not construct the requested logic.",
            "agent": self.name
        }
