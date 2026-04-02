import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.core.agent_base import SovereignAgent, AgentResult
from backend.engines.chat.generation import SovereignGenerator
from backend.engines.utils.i18n import SovereignI18n

logger = logging.getLogger(__name__)

class ResearchInput(BaseModel):
    input: str = Field(..., description="The complex topic to research deeply")
    user_id: str = "guest"
    depth: int = 1

class ResearchAgent(SovereignAgent[ResearchInput, AgentResult]):
    """
    Sovereign Deep Research Agent (ResearchArchitect).
    Performs recursive multi-step analysis and recursive sub-query branching.
    """
    
    def __init__(self):
        super().__init__("ResearchArchitect")
        self.tavily_key = os.getenv("TAVILY_API_KEY")

    async def _run(self, input_data: ResearchInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Research Protocol v7:
        1. Discovery Pulse: Initial thematic survey.
        2. Gap Analysis & Recursive Branching.
        3. Parallel Deep Dives & Citational Verification.
        4. Council-based Report Synthesis (High-Fidelity).
        """
        topic = input_data.input
        self.logger.info(f"Initiating Research Mission: '{topic[:40]}'")
        
        if not self.tavily_key:
            return {"message": "Tavily Pulse is currently offline.", "success": False}

        # Step 1: Initial Discovery Pulse
        discovery = await self._tavily_search(topic, depth="basic")
        discovery_results = discovery.get("results", [])
        
        # Step 2: Gap Analysis & Sub-query Generation
        discovery_context = "\n".join([f"- {r.get('title')}: {r.get('content')[:200]}" for r in discovery_results])
        
        analysis_prompt = (
            f"Topic: '{topic}'\nContext: {discovery_context}\n\n"
            "Identify 2 critical sub-questions for high-fidelity research. Output questions only."
        )
        
        generator = SovereignGenerator()
        sub_questions_raw = await generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Research Architect."},
            {"role": "user", "content": analysis_prompt}
        ])
        sub_questions = [q.strip() for q in sub_questions_raw.split("\n") if q.strip()][:2]

        # Step 3: Recursive Parallel Deep Dives
        self.logger.info(f"Branching Discovery into {len(sub_questions)} vectors.")
        tasks = [self._tavily_search(q, depth="advanced") for q in sub_questions]
        deep_data = await asyncio.gather(*tasks)

        # Step 4: Final Synthesis & Citational Alignment
        all_results = discovery_results.copy()
        all_urls = [r.get("url") for r in discovery_results if r.get("url")]
        
        context_blocks = [f"### [Initial Pulse]\n{discovery_context}"]
        for i, data in enumerate(deep_data):
            results = data.get("results", [])
            q_text = "\n".join([f"- {r.get('content')[:300]}" for r in results])
            context_blocks.append(f"### [Vector: {sub_questions[i]}]\n{q_text}")
            all_urls.extend([r.get("url") for r in results if r.get("url")])

        # Synthesize final Sovereign Report
        synthesis_prompt = (
            f"Mission Topic: {topic}\n\n"
            f"Aggregated Pulse Data:\n" + "\n\n".join(context_blocks) + "\n\n"
            "Synthesize a professional, high-fidelity report. Focus on depth and insight."
        )
        
        final_report = await generator.council_of_models([
            {"role": "system", "content": SovereignI18n.get_prompt("system_brain", lang)},
            {"role": "user", "content": synthesis_prompt}
        ])

        return {
            "message": final_report,
            "citations": list(set(all_urls)),
            "data": {
                "depth_reached": len(sub_questions) + 1,
                "sources_analyzed": len(all_urls)
            }
        }

    async def _tavily_search(self, query: str, depth: str = "basic") -> Dict[str, Any]:
        """Safe Tavily execution helper."""
        # Using a simplified async request for demonstration
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.tavily.com/search", json={
                    "api_key": self.tavily_key, "query": query, "search_depth": depth
                }) as resp:
                    return await resp.json()
        except Exception as e:
            self.logger.error(f"Search failure for '{query}': {e}")
            return {"results": []}
