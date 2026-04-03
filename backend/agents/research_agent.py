"""
Sovereign Deep Research Agent v8.
Performs recursive multi-step analysis and recursive sub-query branching.
Refactored into Autonomous Agent Ecosystem.
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult
from backend.engines.chat.generation import SovereignGenerator
from backend.engines.utils.i18n import SovereignI18n
from backend.core.v8.blackboard import MissionBlackboard

logger = logging.getLogger(__name__)

class ResearchInput(BaseModel):
    input: str = Field(..., description="The complex topic to research deeply")
    user_id: str = "guest"
    session_id: Optional[str] = None
    depth: int = 1

class ResearchAgent(SovereignAgent[ResearchInput, AgentResult]):
    """
    Sovereign Research Architect.
    Executes discovery pulses and recursive parallel deep dives.
    """
    
    def __init__(self):
        super().__init__("ResearchArchitect", use_bus=True)
        self.tavily_key = os.getenv("TAVILY_API_KEY")

    async def _run(self, input_data: ResearchInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Research Protocol v8 Upgrade: Mini-System Orchestration.
        """
        topic = input_data.input
        self.logger.info(f"Initiating Research Mission: '{topic[:40]}'")
        
        if not self.tavily_key:
            return {"message": "Tavily Pulse is currently offline.", "success": False}

        # 1. Pipeline: Search -> Rank -> Summarize
        discovery_results = await self.search(topic, depth="basic")
        
        # 2. Analysis & Sub-query Generation (Self-Expansion)
        sub_questions = await self._generate_sub_queries(topic, discovery_results)
        
        # 3. Parallel Deep Dives
        self.logger.info(f"Branching Discovery into {len(sub_questions)} vectors.")
        tasks = [self.search(q, depth="advanced") for q in sub_questions]
        deep_data = await asyncio.gather(*tasks)
        
        # 4. Aggregation & Ranking
        all_results = discovery_results.copy()
        for data in deep_data:
            all_results.extend(data)
            
        ranked_results = self.rank(all_results)
        
        # 5. Final Synthesis
        summary = await self.summarize(topic, ranked_results, lang=lang)

        # 6. Swarm Integration: Post to Blackboard
        if input_data.session_id:
            blackboard = MissionBlackboard(input_data.session_id)
            await blackboard.post_insight(
                self.id, 
                f"Completed deep research on '{topic}'. Key findings: {summary[:500]}...",
                tag="research_summary"
            )

        # 7. Collaborative Debate: Send to Critic via Agent Bus
        await self.send_message("critic", {
            "from": "research",
            "goal": topic,
            "data": summary
        })
        
        # Wait for feedback from Critic
        self.logger.info("ResearchArchitect is waiting for Critic feedback...")
        feedback_msg = await self.receive_message()
        
        if feedback_msg and feedback_msg.get("success") is False:
            self.logger.warning(f"Critic requested refinement: {feedback_msg.get('feedback')}")
            # In a real scenario, we would refine here. For now, we append the feedback.
            summary = f"{summary}\n\n[Critic Feedback]: {feedback_msg.get('feedback')}"

        return {
            "message": summary,
            "citations": list(set([r.get("url") for r in ranked_results if r.get("url")])),
            "data": {
                "depth_reached": len(sub_questions) + 1,
                "sources_analyzed": len(ranked_results)
            }
        }

    async def search(self, query: str, depth: str = "basic") -> List[Dict[str, Any]]:
        """Integrates search API (Tavily)."""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.tavily.com/search", json={
                    "api_key": self.tavily_key, "query": query, "search_depth": depth
                }) as resp:
                    data = await resp.json()
                    return data.get("results", [])
        except Exception as e:
            self.logger.error(f"Search failure for '{query}': {e}")
            return []

    def rank(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ranks results based on relevance score (dummy or logic)."""
        # Tavily provides score, we use it for sorting
        return sorted(results, key=lambda x: x.get("score", 0), reverse=True)

    async def summarize(self, topic: str, results: List[Dict[str, Any]], lang: str = "en") -> str:
        """Synthesizes high-fidelity reports from ranked data."""
        context = "\n\n".join([f"### {r.get('title')}\nSource: {r.get('url')}\nContent: {r.get('content')[:500]}" for r in results[:10]])
        
        synthesis_prompt = (
            f"Mission Topic: {topic}\n\n"
            f"Aggregated Pulse Data:\n{context}\n\n"
            "Synthesize a professional, high-fidelity report."
        )
        
        generator = SovereignGenerator()
        return await generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Research Architect."},
            {"role": "user", "content": synthesis_prompt}
        ])

    async def _generate_sub_queries(self, topic: str, discovery_results: List[Dict[str, Any]]) -> List[str]:
        """Heuristic for branching research vectors."""
        discovery_context = "\n".join([f"- {r.get('title')}: {r.get('content')[:200]}" for r in discovery_results[:5]])
        analysis_prompt = (
            f"Topic: '{topic}'\nContext: {discovery_context}\n\n"
            "Identify 2 critical sub-questions for high-fidelity research."
        )
        generator = SovereignGenerator()
        raw = await generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Research Architect."},
            {"role": "user", "content": analysis_prompt}
        ])
        return [q.strip() for q in raw.split("\n") if q.strip() and "?" in q][:2]
