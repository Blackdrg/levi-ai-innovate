"""
Sovereign Conversational Agent v15.1.0 GA [STABLE].
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
    Sovereign Dialogue Architect v15.0 GA.
    Engages the 'Council of Models' for non-mocked, high-fidelity synthesis.
    """
    
    def __init__(self):
        super().__init__("DialogueArchitect")

    async def _run(self, input_data: ChatInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Dialogue Protocol v15.1 [SOVEREIGN]:
        1. Multi-Model Council Synthesis.
        2. Cognitive Alignment Calibration (Engine 11).
        3. Sovereign Reflection (Internal Critic).
        """
        query = input_data.input
        self.logger.info(f"Dialogue Mission (V15): '{query[:40]}'")
        
        # 1. Base Synthesis
        response_draft = await handle_local_sync(
            messages=input_data.history + [{"role": "user", "content": f"Mood: {input_data.mood}. Query: {query}"}],
            model_type="default"
        )
        
        # 2. Cognitive Alignment (Engine 11)
        from backend.core.alignment import alignment_engine
        aligned_result = await alignment_engine.calibrate(response_draft, context={"mood": input_data.mood})
        response_aligned = aligned_result["calibrated_output"]
        
        # 3. Sovereign Reflection (Mini-Consensus)
        # If alignment score is low, we iterate once using a stronger model
        if aligned_result["alignment_score"] < 0.8:
            self.logger.warning(f"Low alignment detected ({aligned_result['alignment_score']}). Re-reflecting.")
            response_aligned = await handle_local_sync(
                messages=[
                    {"role": "system", "content": f"You are a master critic. Align the following response to be more {input_data.mood} and brand-safe."},
                    {"role": "user", "content": response_aligned}
                ],
                model_type="L3" # Using L3 (Deep reasoning) for reflection
            )

        return {
            "message": response_aligned,
            "data": {
                "history_length": len(input_data.history),
                "mood": input_data.mood,
                "alignment_score": aligned_result["alignment_score"],
                "calibrated": aligned_result["alignment_score"] < 1.0,
                "version": "15.1.0-GA"
            }
        }
