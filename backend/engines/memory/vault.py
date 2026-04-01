"""
backend/engines/memory/vault.py

Sovereign Memory Vault for LEVI OS v7.
Short-term context and long-term user resonance.
"""

import logging
from typing import Dict, Any, List, Optional
from backend.services.orchestrator.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

class MemoryVault:
    """
    Unified hub for retrieving and synthesizing user memory.
    Connects to Firestore (traits) and FAISS (semantic history).
    """
    
    @staticmethod
    async def recall(user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        1. Access Encrypted Memory Vault (AES-256).
        2. Retrieve Personality Traits (e.g., 'stoicism', 'analytical').
        3. Retrieve Semantic History via Vector Space search.
        4. Synthesize context for the Brain's reasoning engine.
        """
        logger.info(f"[MemoryVault] Recalling memory for user: {user_id}")
        
        # We leverage the hardened v6 MemoryManager as the raw persistence layer.
        combined_ctx = await MemoryManager.get_combined_context(
            user_id=user_id,
            session_id=context.get("session_id", "default"),
            query=context.get("input", "")
        )
        
        return {
            "traits": combined_ctx.get("long_term", {}).get("traits", []),
            "preferences": combined_ctx.get("long_term", {}).get("preferences", []),
            "history_summary": combined_ctx.get("history", [])[-3:]
        }
