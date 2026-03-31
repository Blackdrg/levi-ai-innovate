"""
backend/services/orchestrator/agents/local_agent.py
"""

import logging
from typing import Any, Dict
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from ..local_engine import handle_local

logger = logging.getLogger(__name__)

class LocalInput(BaseModel):
    input: str = Field(..., description="The user's message")
    mood: str = "philosophical"

class LocalAgent(BaseTool[LocalInput, StandardToolOutput]):
    name = "local_agent"
    description = "Fast-path handler for simple queries and greetings."
    input_schema = LocalInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: LocalInput, context: Dict[str, Any]) -> Dict[str, Any]:
        response = handle_local(input_data.input, context)
        
        return {
            "success": True,
            "message": response,
            "agent": self.name
        }
