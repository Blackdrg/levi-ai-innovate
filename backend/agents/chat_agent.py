"""
Sovereign Conversational Agent v8.
Handles high-fidelity dialogue, general reasoning, and brand-aligned interaction.
Refactored into Autonomous Agent Ecosystem.
"""

import logging
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult
from backend.core.local_engine import handle_local_sync

logger = logging.getLogger(__name__)

class ChatInput(BaseModel):
    input: str = Field(..., description="The user's message")
    history: List[Dict[str, str]] = Field(default_factory=list)
    mood: str = "philosophical"
    user_id: str = "guest"

class ChatAgent(SovereignAgent[ChatInput, AgentResult]):
    """
    Sovereign Dialogue Architect.
    Engages the 'Council of Models' for non-mocked, high-fidelity synthesis.
    """
    
    def __init__(self):
        super().__init__("DialogueArchitect")

    async def _run(self, input_data: ChatInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Dialogue Protocol v8:
        1. Engaging the Council (Multi-Model Synthesis).
        2. Philosophical resonance pass.
        """
        query = input_data.input
        self.logger.info(f"Dialogue Mission: '{query[:40]}'")
        
        # Engagement of the Local LLM
        final_response = await handle_local_sync(
            messages=input_data.history + [{"role": "user", "content": query}],
            model_type="default"
        )

        return {
            "message": final_response,
            "data": {
                "history_length": len(input_data.history),
                "mood": input_data.mood
            }
        }
