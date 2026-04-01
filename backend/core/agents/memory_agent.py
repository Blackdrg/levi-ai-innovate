"""
backend/services/orchestrator/agents/memory_agent.py

Memory Agent for LEVI-AI v6.8.8.
Handles long-term and short-term memory retrieval and summarization.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from backend.services.orchestrator.memory_manager import MemoryManager
from backend.generation import generate_chat_response

logger = logging.getLogger(__name__)

class MemoryInput(BaseModel):
    input: str = Field(..., description="The user's question about their past or preferences")
    user_id: str = Field(..., description="User ID for retrieving private memory")
    session_id: Optional[str] = Field("default", description="Current session ID")

class MemoryAgent(BaseTool[MemoryInput, StandardToolOutput]):
    """
    The Memory Agent retrieves and analyzes historical user data and traits.
    """
    
    name = "memory_agent"
    description = "Handles long-term and short-term memory retrieval and summarization."
    input_schema = MemoryInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: MemoryInput, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes memory retrieval and summarizes findings.
        """
        user_id = input_data.user_id
        session_id = input_data.session_id
        query = input_data.input
        
        try:
            # 1. 📂 Fetch combined memory context
            memory_ctx = await MemoryManager.get_combined_context(
                user_id=user_id,
                session_id=session_id,
                query=query
            )
            
            # 2. 🧠 Extract facts and history for the prompt
            long_term = memory_ctx.get("long_term", {})
            traits = long_term.get("traits", [])
            preferences = long_term.get("preferences", [])
            history = memory_ctx.get("history", [])
            
            summary_data = {
                "traits": traits,
                "preferences": preferences,
                "recent_history": history[-5:] if history else []
            }
            
            # 3. ⚡ LLM Synthesis of Memory
            system_prompt = (
                "You are the LEVI Memory Agent. Your job is to answer questions about the user's "
                "personality, past interactions, and stated preferences based on the provided data.\n"
                "Be empathetic, consistent, and helpful. If no info is found, say you remember "
                "the user but don't have that specific detail yet."
            )
            
            prompt = f"Memory Context:\n{summary_data}\n\nUser Question: {query}"
            
            response = await generate_chat_response(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.3
            )
            
            return {
                "success": True,
                "message": response,
                "data": {
                    "memory_points": len(traits) + len(preferences),
                    "context_depth": len(history)
                },
                "agent": self.name
            }

        except Exception as e:
            logger.error(f"[MemoryAgent] failure: {e}")
            return {
                "success": False,
                "error": f"Memory system encountered a barrier: {str(e)}",
                "agent": self.name
            }
