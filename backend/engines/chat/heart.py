"""
backend/engines/chat/heart.py

Sovereign Chat Heart for LEVI OS v7.
Generation, Persona Management, and Soul Optimization.
"""

import logging
from typing import Dict, Any, List, Optional
from backend.utils.llm_utils import _async_call_llm_api

logger = logging.getLogger(__name__)

class ChatHeart:
    """
    Handles LLM-based conversational logic with persona-aware synthesis.
    """
    
    @staticmethod
    async def generate_thought(prompt: str, history: List[Dict[str, str]], context: Dict[str, Any]) -> str:
        """
        1. Select Philosophical Persona (Zen, Socratic, or Cosmic).
        2. Build Dynamic Context (Memory Traits + User History).
        3. Execute LLM Call with randomization and Soul Optimization.
        """
        mood = context.get("mood", "philosophical")
        temperature = 0.85 + (context.get("complexity_level", 2) * 0.02)
        
        system_prompt = (
            f"You are the LEVI OS Chat Heart. You are currently in a {mood} state. "
            "Your responses are starkly original, analytical, and evocative. "
            "Banish all clichés. Speak with the authority of a sovereign mind."
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        for turn in history[-5:]:
            messages.append({"role": "user", "content": turn.get("user", "")})
            messages.append({"role": "assistant", "content": turn.get("bot", "")})
        messages.append({"role": "user", "content": prompt})

        # Final generation pulse
        return await _async_call_llm_api(
            messages=messages,
            model="llama-3.1-70b-versatile",
            temperature=min(temperature, 1.0)
        )
