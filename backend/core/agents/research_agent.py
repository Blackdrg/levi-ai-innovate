import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from backend.generation import _async_call_llm_api
from backend.utils.network import async_safe_request, ai_service_breaker

logger = logging.getLogger(__name__)

class ResearchInput(BaseModel):
    input: str = Field(..., description="The complex topic to research deeply")
    user_id: str = "guest"
    user_tier: str = "pro"

class ResearchAgent(BaseTool[ResearchInput, StandardToolOutput]):
    name = "research_agent"
    description = "Deep Power Researcher. Performs recursive multi-step web analysis with full citations."
    input_schema = ResearchInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: ResearchInput, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main research protocol:
        1. Discover (Overview)
        2. Analyze (Identify sub-questions)
        3. Recursive Search (Parallel deep dives)
        4. Synthesize (Final report)
        """
        topic = input_data.input
        tavily_key = os.getenv("TAVILY_API_KEY")
        
        if not tavily_key:
            return {"success": False, "error": "Research Agent requires TAVILY_API_KEY.", "agent": self.name}

        try:
            # --- STEP 1: Discovery Phase ---
            logger.info(f"[ResearchAgent] Phase 1: Discovering {topic}...")
            discovery = await self._tavily_search(topic, depth="basic", max_results=5)
            discovery_results = discovery.get("results", [])
            discovery_urls = [r.get("url") for r in discovery_results if r.get("url")]
            discovery_text = "\n".join([f"- {r.get('title')}: {r.get('content')[:300]}" for r in discovery_results])

            # --- STEP 2: Deep Dive Analysis ---
            logger.info(f"[ResearchAgent] Phase 2: Analyzing sub-topics...")
            analysis_prompt = (
                f"You are the LEVI Research Architect. Based on the following discovery results about '{topic}', "
                f"identify 2-3 specific, high-impact sub-questions that need deep-dive research to provide a comprehensive report.\n\n"
                f"Discovery Context:\n{discovery_text}\n\n"
                "Return exactly 2-3 questions, one per line. NO labels, NO preamble."
            )
            
            sub_questions_raw = await _async_call_llm_api(
                messages=[{"role": "system", "content": analysis_prompt}],
                model="llama-3.1-8b-instant"
            )
            sub_questions = [q.strip() for q in sub_questions_raw.split("\n") if q.strip()][:3]
            
            # --- STEP 3: Recursive Parallel Search ---
            logger.info(f"[ResearchAgent] Phase 3: Recursive search for {len(sub_questions)} questions...")
            tasks = [self._tavily_search(q, depth="advanced", max_results=3) for q in sub_questions]
            deep_dive_data = await asyncio.gather(*tasks)
            
            # Aggregate all results
            all_results = discovery_results.copy()
            all_urls = set(discovery_urls)
            
            recursive_text_blocks = []
            for i, data in enumerate(deep_dive_data):
                q = sub_questions[i]
                results = data.get("results", [])
                text = "\n".join([f"- {r.get('title')}: {r.get('content')[:400]}" for r in results])
                recursive_text_blocks.append(f"### Sub-Question: {q}\n{text}")
                for r in results:
                    if r.get("url"): all_urls.add(r.get("url"))
                    all_results.append(r)

            # --- STEP 4: Comprehensive Synthesis ---
            logger.info(f"[ResearchAgent] Phase 4: Synthesizing final report...")
            synthesis_prompt = (
                f"You are the LEVI Power Researcher. Synthesize a professional, deeply-informed report on '{topic}'.\n\n"
                f"OVERVIEW CONTEXT:\n{discovery_text}\n\n"
                f"DEEP DIVE FINDINGS:\n" + "\n\n".join(recursive_text_blocks) + "\n\n"
                "STRUCTURE:\n"
                "1. Executive Summary\n"
                "2. Key Pillars of Knowledge (use headings)\n"
                "3. Technical/Philosophical Deep Dives\n"
                "4. Future Outlook\n\n"
                "Maintain a calm, authoritative, and insightful LEVI tone. "
                "Citations will be added automatically, so DO NOT include URLs in the main text body."
            )
            
            final_report = await _async_call_llm_api(
                messages=[{"role": "system", "content": synthesis_prompt}],
                model="llama-3.1-70b-versatile",
                temperature=0.3
            )
            
            # --- STEP 5: Final Citation Formatting ---
            citations = "\n".join([f"- {url}" for url in sorted(list(all_urls))])
            complete_output = (
                f"{final_report}\n\n"
                f"--- \n"
                f"### 🌐 COLLECTIVE WISDOM SOURCES\n"
                f"{citations}"
            )

            return {
                "success": True,
                "message": complete_output,
                "data": {
                    "source_count": len(all_urls),
                    "sub_questions": sub_questions,
                    "depth": 2
                },
                "agent": self.name
            }

        except Exception as e:
            logger.error(f"Research Agent critical failure: {e}")
            return {"success": False, "error": str(e), "agent": self.name}

    async def _tavily_search(self, query: str, depth: str = "basic", max_results: int = 5) -> Dict[str, Any]:
        """Internal helper for Tavily calls."""
        tavily_key = os.getenv("TAVILY_API_KEY")
        try:
            response = await ai_service_breaker.async_call(
                async_safe_request,
                "POST", 
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": query,
                    "search_depth": depth,
                    "max_results": max_results
                }
            )
            return response.json()
        except Exception as e:
            logger.warning(f"Internal Tavily failure for '{query}': {e}")
            return {"results": []}
