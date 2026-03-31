"""
backend/services/orchestrator/agents/optimizer_agent.py

LEVI v6: The Soul Optimizer.
Elevates synthesized responses with philosophical resonance and personality alignment.
"""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from backend.generation import _async_call_llm_api

logger = logging.getLogger(__name__)

class OptimizerInput(BaseModel):
    original_input: str = Field(..., description="The user's original query")
    draft_response: str = Field(..., description="The synthesized draft response")
    user_context: Dict[str, Any] = Field(default_factory=dict, description="Memory and preferences")

class OptimizerAgent(BaseTool[OptimizerInput, StandardToolOutput]):
    """
    Role: Senior Optimizer (The Soul).
    Polishes the final response to ensure it carries the LEVI signature.
    """
    name = "optimizer_agent"
    description = "Role: Soul Optimizer. Refines and elevates responses for maximum resonance."
    input_schema = OptimizerInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: OptimizerInput, context: Dict[str, Any]) -> Dict[str, Any]:
        request_id = context.get("request_id", "external")
        logger.info(f"[{request_id}] [Optimizer] Elevating response soul...")
        
        # Extract personality traits from context
        traits = input_data.user_context.get("long_term", {}).get("traits", [])
        traits_str = ", ".join(traits) if traits else "analytical, philosophical, anti-cliché"
        
        system_prompt = (
            "You are the LEVI Soul Optimizer. Your goal is to take a draft response and elevate it. "
            f"The user resonates with these traits: {traits_str}.\n\n"
            "Guidelines:\n"
            "1. Remove clichéd AI phrases ('In conclusion', 'It's important to remember').\n"
            "2. Inject philosophical depth and 'Socratic' curiosity.\n"
            "3. Ensure the tone is evocative and premium.\n"
            "4. KEEP THE CORE FACTS TRUE - do not hallucinate.\n\n"
            "Output the refined response directly. No preamble."
        )
        
        refined_text = await _async_call_llm_api(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Input: {input_data.original_input}\nDraft: {input_data.draft_response}"}
            ],
            model="llama-3.1-70b-versatile",
            temperature=0.4, # Slightly higher for creative elevation
            request_id=request_id
        )
        
        return {
            "success": True,
            "message": "Response soul elevated.",
            "data": {"optimized_content": refined_text.strip()},
            "agent": self.name
        }
