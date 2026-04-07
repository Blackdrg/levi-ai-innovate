import logging
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from .base import BaseV8Agent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class ChatInput(BaseModel):
    input: str = Field(..., description="The user's message")
    history: List[Dict[str, str]] = Field(default_factory=list)
    mood: str = "philosophical"
    user_id: str = "guest"
    swarm_pass: int = 0

class ChatAgentV8(BaseV8Agent[ChatInput]):
    """
    Sovereign Dialogue Architect v8.7.
    Engages the 'Council of Models' for non-mocked, high-fidelity synthesis.
    Integrated into the Swarm Orchestration logic.
    """
    
    def __init__(self):
        super().__init__("ChatAgentV8")
        self.generator = SovereignGenerator()

    async def _execute_system(self, input_data: ChatInput, context: Dict[str, Any]) -> AgentResult:
        """
        Processes conversational missions with evolutionary intelligence.
        """
        query = input_data.input
        history = input_data.history
        mood = input_data.mood
        
        self.logger.info(f"[Chat-V8] Processing mission: '{query[:40]}...' (Mood: {mood})")
        
        # 1. Council of Models Engagement
        # We inject the mood into the system prompt for diversity
        system_prompt = f"You are LEVI-AI, a sovereign intelligence. Current cognitive state: {mood}. Maintain absolute fidelity."
        
        messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": query}]
        
        # 2. Synthetic Generation
        # V8 use-case: If in a swarm, we might use slightly different temperatures
        temperature = 0.7 if mood == "creative" else 0.2
        
        final_response = await self.generator.council_of_models(
            messages=messages,
            temperature=temperature
        )
        
        return AgentResult(
            success=True,
            message=final_response,
            data={
                "history_length": len(history),
                "mood_applied": mood,
                "swarm_pass": input_data.swarm_pass
            }
        )
