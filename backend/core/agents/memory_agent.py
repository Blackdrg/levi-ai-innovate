import logging
from typing import Dict, Any
from pydantic import BaseModel, Field
from backend.core.agent_base import SovereignAgent, AgentResult
from backend.engines.memory.vault import MemoryVault
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class MemoryInput(BaseModel):
    input: str = Field(..., description="The query about past interactions or user traits")
    user_id: str = "guest"
    session_id: str = "default"

class MemoryAgent(SovereignAgent[MemoryInput, AgentResult]):
    """
    Sovereign Memory Agent (MemoryAgent).
    Coordinates between short-term context and long-term user resonance.
    """
    
    def __init__(self):
        super().__init__("MemoryAgent")

    async def _run(self, input_data: MemoryInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Recall Protocol v7:
        1. Contextual Retrieval (FAISS Vault).
        2. Trait Synthesis & History Compression.
        3. Council-based Memory-Aware Synthesis (High-Fidelity).
        """
        user_id = input_data.user_id
        query = input_data.input
        self.logger.info(f"Recalling Memory Mission for {user_id}: '{query[:40]}'")

        # 1. Engage Memory Vault (FAISS/Firestore Bridge)
        memory_data = await MemoryVault.get_combined_context(user_id, query)
        
        traits = memory_data.get("long_term", {}).get("traits", [])
        preferences = memory_data.get("long_term", {}).get("preferences", [])
        semantic_hits = memory_data.get("semantic_results", [])

        # 2. Build Synthesis Context (Crystallized Wisdom)
        summary_context = (
            f"User Archetype Traits: {', '.join(traits) if traits else 'Unknown'}\n"
            f"Observed Preferences: {', '.join(preferences) if preferences else 'Unknown'}\n"
            f"Crystallized Fragments: {len(semantic_hits)} relevant patterns detected."
        )

        # 3. Final Memory-Aware Synthesis
        system_prompt = (
            "You are the LEVI Memory Agent. Your role is to provide continuity and resonance.\n"
            "Use the crystallized context to address the user mission with historical depth.\n"
            "Technical Requirements:\n"
            "- Integrity: If no specific memory exists, do not fabricate.\n"
            "- Depth: Speak to the user's observed traits and preferences.\n"
        )
        
        generator = SovereignGenerator()
        
        # Engage the Council for maximum contextual resonance
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
