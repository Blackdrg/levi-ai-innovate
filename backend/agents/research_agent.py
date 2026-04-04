import os
import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult
from backend.engines.chat.generation import SovereignGenerator
from backend.broadcast_utils import SovereignBroadcaster

logger = logging.getLogger(__name__)

class ResearchInput(BaseModel):
    input: str = Field(..., description="The complex topic to research deeply")
    user_id: str = "guest"
    session_id: Optional[str] = None
    depth: int = 1

class ResearchAgent(SovereignAgent[ResearchInput, AgentResult]):
    """
    Sovereign Research Architect (v13.0.0).
    Executes binary discovery pulses and SQL-backed recursive branching.
    """
    
    def __init__(self):
        super().__init__("ResearchArchitect", use_bus=True)
        self.tavily_key = os.getenv("TAVILY_API_KEY")

    async def _run(self, input_data: ResearchInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Research Protocol v13.0: Unified Cognitive Discovery.
        """
        topic = input_data.input
        session_id = input_data.session_id or "research_v13"
        
        # Emit Pulse: Mission Start
        SovereignBroadcaster.broadcast({
            "type": "AGENT_RESEARCH_START",
            "agent": self.id,
            "topic": topic
        })

        if not self.tavily_key:
            return {"message": "Tavily Pulse is currently offline.", "success": False}

        # 1. Discovery Pulse (Basic)
        discovery_results = await self.search(topic, depth="basic", session_id=session_id)
        
        # 2. Branching Logic (Sovereign Expansion)
        sub_questions = await self._generate_sub_queries(topic, discovery_results)
        
        # Emit Pulse: Branching Vector
        if sub_questions:
            SovereignBroadcaster.broadcast({
                "type": "AGENT_BRANCHING",
                "agent": self.id,
                "vectors": len(sub_questions),
                "data": {"queries": sub_questions}
            })

        # 3. Parallel Deep Dives
        tasks = [self.search(q, depth="advanced", session_id=session_id) for q in sub_questions]
        deep_data = await asyncio.gather(*tasks)
        
        # 4. Aggregation
        all_results = discovery_results.copy()
        for data in deep_data: all_results.extend(data)
        ranked = sorted(all_results, key=lambda x: x.get("score", 0), reverse=True)
        
        # 5. SQL Persistence (Absolute Monolith v13)
        summary = await self.summarize(topic, ranked, lang=lang)
        await self._persist_insight(session_id, topic, {"summary": summary, "vectors": len(sub_questions)})

        # 6. Critic Bridge (Consensus)
        await self.send_message("critic", {"from": "research", "goal": topic, "data": summary})
        
        # Synchronous Handshake for finality
        feedback = await self.receive_message()
        if feedback and feedback.get("success") is False:
             summary = f"{summary}\n\n[REFINEMENT]: {feedback.get('feedback')}"

        return {
            "message": summary,
            "citations": list(set([r.get("url") for r in ranked if r.get("url")])),
            "data": {"sources": len(ranked), "v13_trace": True}
        }

    async def search(self, query: str, depth: str = "basic", session_id: str = "v13") -> List[Dict[str, Any]]:
        """Integrated Search with Discovery Pulse."""
        SovereignBroadcaster.broadcast({"type": "AGENT_SEARCH_RESULT", "agent": self.id, "query": query})
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.tavily.com/search", json={
                    "api_key": self.tavily_key, "query": query, "search_depth": depth
                }) as resp:
                    data = await resp.json()
                    return data.get("results", [])
        except Exception:
            return []

    async def _persist_insight(self, session_id: str, topic: str, data: Dict[str, Any]):
        """Saves research to SQL agent_insights fabric."""
        try:
            from backend.db.postgres_db import get_write_session
            from sqlalchemy import text
            async with get_write_session() as session:
                await session.execute(
                    text("INSERT INTO agent_insights (session_id, agent_id, topic, data, tag) VALUES (:sid, :aid, :top, :data, 'discovery')"),
                    {"sid": session_id, "aid": self.id, "top": topic, "data": json.dumps(data)}
                )
        except Exception as e:
            logger.error(f"[Research-v13] SQL Insight failure: {e}")

    async def summarize(self, topic: str, results: List[Dict[str, Any]], lang: str = "en") -> str:
        context = "\n".join([f"### {r.get('title')}\nSource: {r.get('url')}\nContent: {r.get('content')[:500]}" for r in results[:5]])
        generator = SovereignGenerator()
        return await generator.council_of_models([
            {"role": "system", "content": "You are the LEVI v13 Research Architect."},
            {"role": "user", "content": f"Synthesize v13 report on: {topic}\n\n{context}"}
        ])

    async def _generate_sub_queries(self, topic: str, results: List[Dict[str, Any]]) -> List[str]:
        generator = SovereignGenerator()
        raw = await generator.council_of_models([
            {"role": "system", "content": "You are the LEVI v13 Research Architect."},
            {"role": "user", "content": f"Topic: '{topic}'\nIdentify 2 sub-questions."}
        ])
        return [q.strip() for q in raw.split("\n") if q.strip() and "?" in q][:2]
