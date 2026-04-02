import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from .base import BaseV8Agent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class ResearchInput(BaseModel):
    input: str = Field(..., description="Topic for deep research")
    depth: int = 2

class ResearchAgentV8(BaseV8Agent[ResearchInput]):
    """
    LeviBrain v8: Deep Research System
    Scraper + Ranker + Summarizer
    """

    def __init__(self):
        super().__init__("ResearchAgentV8")
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        self.generator = SovereignGenerator()

    async def _execute_system(self, input_data: ResearchInput, context: Dict[str, Any]) -> AgentResult:
        topic = input_data.input
        self.logger.info(f"[Research-V8] starting system operation for: {topic}")
        
        if not self.tavily_key:
            return AgentResult(success=False, error="Search API missing.")

        # 1. Scraper: Multi-vector discovery
        discovery_tasks = [
            self._tavily_search(topic, depth="basic"),
            self._tavily_search(f"{topic} latest research and news", depth="advanced")
        ]
        discovery_results = await asyncio.gather(*discovery_tasks)
        
        all_raw_results = []
        for res in discovery_results:
            all_raw_results.extend(res.get("results", []))

        # 2. Ranker: LLM scoring of source quality
        ranked_results = await self._rank_sources(topic, all_raw_results)
        
        # 3. Summarizer: High-fidelity synthesis
        final_summary = await self._summarize_findings(topic, ranked_results)
        
        urls = [r.get("url") for r in ranked_results if r.get("url")]
        
        return AgentResult(
            success=True,
            message=final_summary,
            citations=list(set(urls)),
            data={
                "ranked_sources_count": len(ranked_results),
                "total_sources_analyzed": len(all_raw_results)
            }
        )

    async def _rank_sources(self, topic: str, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ranker system pass."""
        if not sources: return []
        
        # Take top 10 for ranking to save context
        to_rank = sources[:10]
        context = "\n".join([f"ID: {i} | Title: {s.get('title')} | Snippet: {s.get('content')[:150]}" for i, s in enumerate(to_rank)])
        
        rank_prompt = (
            f"Topic: {topic}\n"
            f"Sources:\n{context}\n\n"
            "Rank these sources based on relevance and quality (0.0 - 1.0).\n"
            "Return JSON: {\"ranks\": [{\"id\": 0, \"score\": 0.95}, ...]}"
        )
        
        try:
            raw_res = await self.generator.council_of_models([
                {"role": "system", "content": "You are the LEVI Ranker."},
                {"role": "user", "content": rank_prompt}
            ])
            # Simplified parsing for logic walkthrough
            import json
            import re
            json_match = re.search(r"\{.*\}", raw_res, re.DOTALL)
            if json_match:
                 data = json.loads(json_match.group(0))
                 ranks = {item["id"]: item["score"] for item in data.get("ranks", [])}
                 # Filter and Sort
                 ranked = sorted([s for i, s in enumerate(to_rank) if i in ranks and ranks[i] > 0.6], 
                                 key=lambda x: ranks.get(to_rank.index(x), 0), reverse=True)
                 return ranked
        except Exception as e:
            self.logger.warning(f"Ranking pass failed: {e}")
            
        return sources[:5] # Fallback to top 5

    async def _summarize_findings(self, topic: str, results: List[Dict[str, Any]]) -> str:
        """Summarizer pass."""
        context = "\n\n".join([f"Source: {r.get('title')}\nContent: {r.get('content')}" for r in results])
        
        synth_prompt = (
            f"Research Topic: {topic}\n\n"
            f"Context:\n{context}\n\n"
            "Synthesize a deep, investigative report that reveals hidden patterns and critical insights."
        )
        
        return await self.generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Master Summarizer."},
            {"role": "user", "content": synth_prompt}
        ])

    async def _tavily_search(self, query: str, depth: str = "basic") -> Dict[str, Any]:
        """Safe Tavily execution helper."""
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
