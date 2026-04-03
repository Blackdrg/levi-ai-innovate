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
        self.logger.info(f"[Research-V8] Initiating high-fidelity investigation for: {topic}")
        
        if not self.tavily_key:
            self.logger.warning("[Research-V8] Tavily offline. Falling back to Sovereign Vector Intelligence.")
            return await self._execute_local_fallback(topic, context)

        # 1. Scraper: Multi-vector Discovery
        discovery_tasks = [
            self._tavily_search(topic, depth="basic"),
            self._tavily_search(f"detailed status and deep analysis of {topic}", depth="advanced")
        ]
        discovery_results = await asyncio.gather(*discovery_tasks)
        
        all_raw_results = []
        for res in discovery_results:
            all_raw_results.extend(res.get("results", []))

        if not all_raw_results:
            return AgentResult(success=False, error="No external data intelligence could be gathered.")

        # 2. Ranker: Precision Source Analysis (Pass 1)
        ranked_results = await self._rank_sources(topic, all_raw_results)
        
        # 3. Summarizer: Investigative Synthesis (Pass 2)
        final_report = await self._summarize_findings(topic, ranked_results)
        
        urls = [r.get("url") for r in ranked_results if r.get("url")]
        
        return AgentResult(
            success=True,
            message=final_report,
            citations=list(set(urls)),
            data={
                "ranked_count": len(ranked_results),
                "total_analyzed": len(all_raw_results),
                "architecture": "Investigative-v8"
            }
        )

    async def _rank_sources(self, topic: str, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ranker system pass: Evaluates source relevance and depth."""
        if not sources: return []
        
        # Take top 12 for precision ranking
        to_rank = sources[:12]
        context = "\n".join([f"Source [{i}]: {s.get('title')} | Snippet: {s.get('content')[:200]}" for i, s in enumerate(to_rank)])
        
        rank_prompt = (
            f"RESEARCH TOPIC: {topic}\n"
            f"DISCOVERED SOURCES:\n{context}\n\n"
            "Task: Score each source for depth, authority, and relevance (0.0-1.0).\n"
            "Identify the 'Critical Core' - the most investigative sources.\n"
            "Return JSON: {\"ranks\": [{\"id\": 0, \"score\": 0.95}, ...]}"
        )
        
        try:
            raw_res = await self.generator.council_of_models([
                {"role": "system", "content": "You are the LEVI Ranker."},
                {"role": "user", "content": rank_prompt}
            ])
            import json as json_lib
            import re
            match = re.search(r"\{.*\}", raw_res, re.DOTALL)
            if match:
                 data = json_lib.loads(match.group(0))
                 ranks = {item["id"]: item["score"] for item in data.get("ranks", [])}
                 # Sort by score and filter out low-quality noise
                 ranked = sorted([s for i, s in enumerate(to_rank) if i in ranks and ranks[i] > 0.65], 
                                 key=lambda x: ranks.get(to_rank.index(x), 0), reverse=True)
                 return ranked[:8]
        except Exception as e:
            self.logger.warning(f"Precision ranking pass failed: {e}")
            
        return sources[:6] # Fallback to top-k

    async def _summarize_findings(self, topic: str, results: List[Dict[str, Any]]) -> str:
        """Summarizer pass: Investigative Synthesis."""
        corpus = "\n\n".join([f"[Source: {r.get('title')}]: {r.get('content')}" for r in results])
        
        synth_prompt = (
            f"INVESTIGATIVE TOPIC: {topic}\n\n"
            f"RESEARCH CORPUS:\n{corpus}\n\n"
            "Task: Produce a high-fidelity intelligence report. Focus on hidden patterns, critical risks, and emerging opportunities.\n"
            "Use formal citations [1][2]... and maintain a deep, investigative tone."
        )
        
        return await self.generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Master Investigator."},
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

    async def _execute_local_fallback(self, topic: str, context: Dict[str, Any]) -> AgentResult:
        """Fallback mission using internal knowledge and vector resonance."""
        from backend.db.vector_store import VectorDB
        try:
            user_id = context.get("user_id", "system")
            kb = await VectorDB.get_user_collection(user_id, "knowledge")
            results = await kb.search(topic, limit=10)
            
            if not results:
                return AgentResult(success=False, error="Local neural resonance found no matches for this topic.")
            
            corpus = "\n".join([f"- {r.get('text')}" for r in results])
            summary = await self.generator.council_of_models([
                {"role": "system", "content": "You are the LEVI Internal Researcher. Summarize the following internal knowledge based on the user topic."},
                {"role": "user", "content": f"Topic: {topic}\nInternal Corpus:\n{corpus}"}
            ])
            
            return AgentResult(
                success=True,
                message=summary + "\n\n*(Note: This intelligence was gathered from internal Sovereign memory as external links are offline.)*",
                data={"source": "local_vector_kb"}
            )
        except Exception as e:
            return AgentResult(success=False, error=f"Local research failure: {str(e)}")
