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

class SourceModel(BaseModel):
    title: str
    url: str
    snippet: str
    score: float = 0.0

class ResearchData(BaseModel):
    topic: str
    sources: List[SourceModel]
    primary_themes: List[str] = Field(default_factory=list)
    total_analyzed: int
    architecture: str = "Investigative-v8"

class ResearchAgentV8(BaseV8Agent[ResearchInput]):
    """
    LeviBrain v8: Deep Research System
    Scraper + Ranker + Data Collector
    """

    def __init__(self):
        super().__init__("ResearchAgentV8")
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        self.generator = SovereignGenerator()

    async def _execute_system(self, input_data: ResearchInput, context: Dict[str, Any]) -> AgentResult[ResearchData]:
        topic = input_data.input
        self.logger.info(f"[Research-V8] Initiating structured investigation for: {topic}")
        
        # 1. Swarm-Aware Discovery: Delegate to Search Agent if possible
        # This reduces direct API dependency and leverages the common search interface
        self.logger.info(f"[Research-V8] Delegating primary discovery to Search Agent...")
        search_res = await self.delegate_to("search_agent", {"query": topic}, context)
        
        all_raw_results = []
        if search_res.success and isinstance(search_res.data, dict):
            # Extract results from the search agent's standardized output
            all_raw_results.extend(search_res.data.get("results", []))
            self.logger.info(f"[Research-V8] Swarm discovery yielded {len(all_raw_results)} initial vectors.")

        # 1.5. Fallback/Augment with direct Tavily if key exists and swarm was insufficient
        if not all_raw_results and not self.tavily_key:
            self.logger.warning("[Research-V8] Swarm discovery failed and Tavily offline. Local fallback.")
            return await self._execute_local_fallback(topic, context)
            
        if self.tavily_key and len(all_raw_results) < 5:
            self.logger.info(f"[Research-V8] Augmenting swarm data with direct investigative search.")
            discovery_tasks = [
                self._tavily_search(topic, depth="basic")
            ]
            discovery_results = await asyncio.gather(*discovery_tasks)
            for res in discovery_results:
                all_raw_results.extend(res.get("results", []))

        if not all_raw_results:
            return AgentResult(success=False, error="No external or swarm-based intelligence could be gathered for this mission.")

        # 2. Ranker: Precision Source Analysis
        # We still use the LLM to Rank, but it returns JSON, not a final answer
        ranked_nodes = await self._rank_sources(topic, all_raw_results)
        
        # 3. Theme Extraction (New: Extract themes from ranked results)
        themes = await self._extract_themes(topic, ranked_nodes)
        
        structured_sources = [
            SourceModel(
                title=r.get("title", "Unknown"),
                url=r.get("url", ""),
                snippet=r.get("content", ""),
                score=r.get("score", 0.0)
            ) for r in ranked_nodes
        ]

        return AgentResult(
            success=True,
            message=f"Investigation complete. {len(structured_sources)} primary intelligence vectors identified.",
            citations=[s.url for s in structured_sources if s.url],
            data=ResearchData(
                topic=topic,
                sources=structured_sources,
                primary_themes=themes,
                total_analyzed=len(all_raw_results)
            )
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

    async def _extract_themes(self, topic: str, results: List[Dict[str, Any]]) -> List[str]:
        """Theme Extraction pass: Identifies primary investigative vectors."""
        if not results: return []
        
        corpus = "\n".join([f"- {r.get('title')}: {r.get('content')[:150]}" for r in results[:5]])
        
        theme_prompt = (
            f"TOPIC: {topic}\n"
            f"CORPUS SNIPPET:\n{corpus}\n\n"
            "Identify 3-5 primary research themes or investigative vectors.\n"
            "Return a simple comma-separated list."
        )
        
        try:
            res = await self.generator.council_of_models([
                {"role": "system", "content": "You are the LEVI Intelligence Analyst."},
                {"role": "user", "content": theme_prompt}
            ])
            return [t.strip() for t in res.split(",") if t.strip()][:5]
        except:
            return ["General Investigation"]

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
