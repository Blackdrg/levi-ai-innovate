"""
Sovereign Memory Agent v8.
Coordinates between short-term context and long-term user resonance.
Refactored into Autonomous Agent Ecosystem.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class MemoryInput(BaseModel):
    input: str = Field(..., description="The query about past interactions or user traits")
    user_id: str = "guest"
    session_id: str = "default"

class MemoryAgent(SovereignAgent[MemoryInput, AgentResult]):
    """
    Sovereign Memory Architect.
    Coordinates between short-term context and long-term user resonance via Memory Vault.
    """
    
    def __init__(self):
        super().__init__("MemoryAgent")

    async def _run(self, input_data: MemoryInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Recall Protocol v8:
        1. Contextual Retrieval (FAISS Vault).
        2. Trait Synthesis.
        3. Memory-Aware Council Synthesis.
        """
        user_id = input_data.user_id
        query = input_data.input
        self.logger.info(f"Recalling Memory Mission for {user_id}: '{query[:40]}'")

        # 1. Engage Memory Vault (v8 Bridge)
        from backend.memory.manager import MemoryManager
        memory_manager = MemoryManager()
        history = await memory_manager.get_context(user_id)
        
        # We also fetch the full v8 context for depth
        memory_data = await memory_manager.get_combined_context(user_id, input_data.session_id, query)

        
        traits = memory_data.get("long_term", {}).get("traits", [])
        preferences = memory_data.get("long_term", {}).get("preferences", [])
        semantic_hits = memory_data.get("semantic_results", [])

        # 2. Build Synthesis Context
        summary_context = (
            f"User Archetype Traits: {', '.join(traits) if traits else 'Unknown'}\n"
            f"Observed Preferences: {', '.join(preferences) if preferences else 'Unknown'}\n"
            f"Recent Dialogue: {len(history)} mission fragments analyzed."
        )

        # 3. Final Memory-Aware Synthesis
        system_prompt = (
            "You are the LEVI Memory Agent. Your role is to provide continuity and resonance.\n"
            "Use the crystallized context to address the user mission with historical depth.\n"
        )
        
        generator = SovereignGenerator()
        
        final_response = await generator.council_of_models([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Memory Context: {summary_context}\n\nMission: {query}"}
        ])

        return {
            "message": final_response,
            "data": {
                "traits_detected": len(traits),
                "semantic_resonance": len(semantic_hits),
                "user_id": user_id
            }
        }
