import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.core.agent_base import SovereignAgent, AgentResult
from backend.engines.chat.chat_engine import ChatEngine as ChatEngineCore
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class ChatInput(BaseModel):
    input: str = Field(..., description="The user's message")
    history: List[Dict[str, str]] = Field(default_factory=list)
    mood: str = "philosophical"
    user_id: str = "guest"

class ChatAgent(SovereignAgent[ChatInput, AgentResult]):
    """
    Sovereign Conversational Agent (DialogueArchitect).
    Handles high-fidelity dialogue, general reasoning, and brand-aligned interaction.
    """
    
    def __init__(self):
        super().__init__("DialogueArchitect")
        # Engines are initialized per mission to ensure thread-safety in high-concurrency environments

    async def _run(self, input_data: ChatInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Dialogue Protocol v7:
        1. Contextual Verification.
        2. Council-based Synthesis (Philosophical/Brand Aligned).
        """
        query = input_data.input
        self.logger.info(f"Dialogue Mission: '{query[:40]}'")
        
        generator = SovereignGenerator()
        
        # Engage the Council of Models for high-fidelity synthesis
        # This ensures the response is non-mocked and globally ready.
        final_response = await generator.council_of_models(
            messages=input_data.history + [{"role": "user", "content": query}]
        )

        return {
            "message": final_response,
            "data": {
                "history_length": len(input_data.history),
                "mood": input_data.mood
            }
        }
