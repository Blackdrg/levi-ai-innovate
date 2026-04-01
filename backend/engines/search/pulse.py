"""
backend/engines/search/pulse.py

Sovereign Search Pulse for LEVI OS v7.
Deep Research Protocol with Recursive Discovery.
"""

import logging
from typing import Dict, Any, List, Optional
from backend.services.orchestrator.agents.research_agent import ResearchAgent

logger = logging.getLogger(__name__)

class SearchPulse:
    """
    Executes deep research and recursive search.
    Connects to the v6.8.8 research_agent for high-fidelity discovery.
    """
    
    @staticmethod
    async def perform_deep_research(query: str, user_id: str, context: Dict[str, Any]) -> str:
        """
        1. Discover (Overview).
        2. Analyze (Sub-questions).
        3. Recursive Search (Parallel deep dives).
        4. Synthesize (Final report with global citations).
        """
        logger.info(f"[SearchPulse] Initiating Deep Research for: {query[:40]}")
        
        # We leverage the hardened v6 ResearchAgent as the core discovery engine.
        agent = ResearchAgent()
        result = await agent.execute({
            "input": query,
            "user_id": user_id,
            "user_tier": context.get("user_tier", "pro")
        }, context)
        
        return result.message if result.success else "The search pulse was unable to discover definitive context."
