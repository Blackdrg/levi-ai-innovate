"""
Sovereign Context Manager v8.
Manages token budgeting, context hydration, and memory-aware pruning.
Ensures optimized token allocation across instructions, history, and examples.
"""

import logging
import json
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class TokenBudget:
    """
    Representation of the token allocation for a single request.
    Defaults for Llama 3.1 8B (8k context window).
    """
    total_max: int = 4096
    instruction_limit: int = 1500
    history_limit: int = 800
    example_limit: int = 1000
    reserved_for_output: int = 796

    def dict(self):
        return asdict(self)

class ContextManager:
    """
    LeviBrain v8: Context Manager.
    Handles atmospheric context hydration and budget allocation.
    """

    def allocate_budget(self, intent_type: str, user_tier: str, complexity: int) -> TokenBudget:
        """
        Dynamically divides tokens between context components based on request type and tier.
        """
        # Base Budget
        budget = TokenBudget()
        
        # 1. Tier-Based Total Limit
        if user_tier in ("pro", "creator"):
            budget.total_max = 8192
            budget.reserved_for_output = 1500
        else:
            budget.total_max = 4096
        
        # 2. Intent-Based Allocation
        if intent_type == "creative" or complexity >= 3:
            budget.example_limit = 1500
            budget.history_limit = 1000
            budget.instruction_limit = 1200
        elif intent_type == "code":
            budget.history_limit = 1500
            budget.example_limit = 500
            budget.reserved_for_output = 1200
        else:
            budget.instruction_limit = 1000
            budget.example_limit = 800
            budget.history_limit = 1000

        return budget

    def compress_pattern(self, input_text: str, output_text: str, max_chars: int = 300) -> str:
        """
        Compresses a success pattern into a high-density format: Q: {in} -> A: {out}
        """
        in_len = int(max_chars * 0.3)
        out_len = int(max_chars * 0.7)
        
        compressed_in = input_text[:in_len] + ("..." if len(input_text) > in_len else "")
        compressed_out = (output_text[:out_len] + ("..." if len(output_text) > out_len else "")).replace("\n", " ")
        
        return f"Q: {compressed_in} -> A: {compressed_out}"

    async def hydrate_context(self, raw_context: Dict[str, Any], budget: TokenBudget) -> Dict[str, Any]:
        """
        Phase 3.7: Self-Optimized Context Hydration.
        Prunes and prioritizes context, using LLM-based distillation for history if budget is exceeded.
        """
        hydrated = raw_context.copy()
        history = hydrated.get("history", [])
        
        # 1. Distillation Check (Phase 3.7)
        history_str = json.dumps(history)
        if len(history_str.split()) > budget.history_limit: # Token-ish count
            logger.info(f"🧠 [Context] History exceeds budget ({len(history_str.split())} tokens). Triggering distillation...")
            hydrated["history"] = await self.distill_history(history)
        
        # 2. Prune examples
        examples = hydrated.get("examples", [])
        if len(json.dumps(examples).split()) > budget.example_limit:
            hydrated["examples"] = examples[:3] # Keep only top 3
            
        return hydrated

    async def distill_history(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Uses a lightweight model to distill history into a dense summary.
        """
        from backend.services.brain_service import brain_service
        
        history_text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in history])
        prompt = f"Distill the following conversation into a dense, context-heavy summary (max 300 words):\n\n{history_text}"
        
        try:
            summary = await brain_service.call_local_llm(prompt, model="llama3.1:8b")
            return [{"role": "system", "content": f"PREVIOUS CONTEXT SUMMARY: {summary}"}]
        except Exception as e:
            logger.error(f"[Context] Distillation failed: {e}")
            return history[-2:] # Panic fallback: last 2 messages
