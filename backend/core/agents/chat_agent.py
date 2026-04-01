"""
backend/services/orchestrator/agents/chat_agent.py
"""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from backend.generation import generate_response

logger = logging.getLogger(__name__)

class ChatInput(BaseModel):
    input: str = Field(..., description="The user's message")
    history: List[Dict[str, str]] = Field(default_factory=list, description="Conversation history")
    mood: str = "philosophical"
    user_tier: str = "free"
    user_id: str = "guest"

class ChatAgent(BaseTool[ChatInput, StandardToolOutput]):
    name = "chat_agent"
    description = "Handles conversational interaction and general reasoning."
    input_schema = ChatInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: ChatInput, context: Dict[str, Any]) -> Dict[str, Any]:
        response = await generate_response(
            prompt=input_data.input,
            history=input_data.history,
            mood=input_data.mood,
            user_tier=input_data.user_tier
        )
        
        return {
            "success": True,
            "message": response,
            "agent": self.name
        }
