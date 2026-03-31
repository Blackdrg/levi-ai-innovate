"""
backend/services/orchestrator/context_utils.py

Context Budgeting & Token Management for LEVI-AI (Phase 17).
Ensures optimized token allocation across instructions, history, and examples.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

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

def allocate_budget(intent_type: str, user_tier: str, complexity: int) -> TokenBudget:
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
        # Prioritize examples and history for complex reasoning
        budget.example_limit = 1500
        budget.history_limit = 1000
        budget.instruction_limit = 1200
    elif intent_type == "code":
        # Prioritize history and larger output room
        budget.history_limit = 1500
        budget.example_limit = 500
        budget.reserved_for_output = 1200
    else:
        # Standard conversational (Balanced)
        budget.instruction_limit = 1000
        budget.example_limit = 800
        budget.history_limit = 1000

    return budget

def compress_pattern(input_text: str, output_text: str, max_chars: int = 300) -> str:
    """
    Compresses a success pattern into a high-density format: Q: {in} -> A: {out}
    Used to save context space in few-shot injections.
    """
    # Truncate to preserve budget while keeping the 'vibe'
    in_len = int(max_chars * 0.3)
    out_len = int(max_chars * 0.7)
    
    compressed_in = input_text[:in_len] + ("..." if len(input_text) > in_len else "")
    compressed_out = (output_text[:out_len] + ("..." if len(output_text) > out_len else "")).replace("\n", " ")
    
    return f"Q: {compressed_in} -> A: {compressed_out}"
