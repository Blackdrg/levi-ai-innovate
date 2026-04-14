"""
Sovereign Research Agent v13.1 — Multi-Source Synthesis.
Upgrades over v13.0:
  - URL fingerprint deduplication before aggregation
  - Confidence weighting: Tavily score × domain authority
  - Structured CitationBundle output (Neo4j-ingestible triplets)
"""

import os
import asyncio
import hashlib
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

from pydantic import BaseModel, Field
from backend.agents.base import SovereignAgent, AgentResult
from backend.core.local_engine import handle_local_sync
from backend.broadcast_utils import SovereignBroadcaster
from backend.memory.vector_store import SovereignVectorStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain authority tier table (higher = more trustworthy)
# Extend as needed; defaults to 0.5 for unknown domains.
# ---------------------------------------------------------------------------
DOMAIN_AUTHORITY: Dict[str, float] = {
    # Academic / Gov
    "arxiv.org": 0.95, "scholar.google.com": 0.95, "pubmed.ncbi.nlm.nih.gov": 0.95,
    "nature.com": 0.95, "science.org": 0.95, "ieee.org": 0.92,
    ".gov": 0.90, ".edu": 0.88,
    # News / Reference
    "reuters.com": 0.85, "bbc.com": 0.85, "nytimes.com": 0.82,
    "wikipedia.org": 0.80, "britannica.com": 0.82,
    # Tech
    "github.com": 0.78, "stackoverflow.com": 0.75, "docs.python.org": 0.90,
}


def _domain_authority(url: str) -> float:
    """Returns a [0,1] authority score for a URL's domain."""
    try:
        host = urlparse(url).hostname or ""
        # Exact-match first
        if host in DOMAIN_AUTHORITY:
            return DOMAIN_AUTHORITY[host]
        # Suffix-match (e.g. .gov, .edu)
        for suffix, score in DOMAIN_AUTHORITY.items():
            if suffix.startswith(".") and host.endswith(suffix):
                return score
        return 0.5
    except Exception:
        return 0.5


def _url_fingerprint(url: str) -> str:
    """Normalised SHA-256 fingerprint for URL deduplication."""
    normalised = url.strip().lower().rstrip("/")
    return hashlib.sha256(normalised.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# CitationBundle — Neo4j-ingestible citation format
# ---------------------------------------------------------------------------

class CitationSource(BaseModel):
    url: str
    title: str
    snippet: str
    tavily_score: float
    domain_authority: float
    confidence: float           # tavily_score × domain_authority
    fingerprint: str            # URL dedup hash


class CitationBundle(BaseModel):
    """
    Structured output consumed by MemoryAgent to write Neo4j triplets.
    Each source becomes: (topic)-[SOURCED_FROM]->(url_entity)
    """
    topic: str
    summary: str
    sources: List[CitationSource]
    total_sources: int
    deduplicated_sources: int


# ---------------------------------------------------------------------------
# Input / Agent
# ---------------------------------------------------------------------------

class ResearchInput(BaseModel):
    input: str = Field(..., description="The complex topic to research deeply")
    user_id: str = "guest"
    session_id: Optional[str] = None
    depth: int = 1


class ResearchAgent(SovereignAgent[ResearchInput, AgentResult]):
    """
    Sovereign Research Architect v13.1.
    Produces CitationBundle output compatible with MemoryAgent Neo4j ingest.
    """

    def __init__(self):
        super().__init__("ResearchArchitect", use_bus=True)
        self.tavily_key = os.getenv("TAVILY_API_KEY")

    async def _run(self, input_data: ResearchInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        topic      = input_data.input
        session_id = input_data.session_id or "research_v13"

        SovereignBroadcaster.broadcast({
            "type": "AGENT_RESEARCH_START",
            "agent": self.name,
            "topic": topic,
        })

        # 🛡️ Graduation #20: Sovereign-First Intelligence
        # If SOVEREIGN_MODE=True, we block external egress regardless of API key availability.
        sovereign_mode = os.getenv("SOVEREIGN_MODE", "true").lower() == "true"
        
        if sovereign_mode or not self.tavily_key:
            if sovereign_mode:
                self.logger.info("🛡️ [Sovereign-First] External egress suppressed. Utilizing Internal RAG Knowledge Base.")
            else:
                self.logger.warning("Tavily Pulse offline. Escalating to Internal RAG Knowledge Base.")
            return await self._internal_rag_fallback(topic, session_id, lang)

        # ── 1. Discovery pass ─────────────────────────────────────────
        raw_results = await self.search(topic, depth="basic", session_id=session_id)

        # ── 2. Sub-query expansion ────────────────────────────────────
        sub_questions = await self._generate_sub_queries(topic, raw_results)
        if sub_questions:
            SovereignBroadcaster.broadcast({
                "type": "AGENT_BRANCHING",
                "agent": self.name,
                "vectors": len(sub_questions),
                "data": {"queries": sub_questions},
            })

        # ── 3. Parallel deep dives ────────────────────────────────────
        deep_results_batches = await asyncio.gather(
            *[self.search(q, depth="advanced", session_id=session_id) for q in sub_questions]
        )
        for batch in deep_results_batches:
            raw_results.extend(batch)

        # ── 4. Deduplication (URL fingerprint) ────────────────────────
        seen_fp: set = set()
        unique_results = []
        for r in raw_results:
            fp = _url_fingerprint(r.get("url", ""))
            if fp not in seen_fp:
                seen_fp.add(fp)
                unique_results.append(r)

        # ── 5. Confidence weighting ───────────────────────────────────
        weighted: List[Tuple[float, Dict]] = []
        for r in unique_results:
            t_score = float(r.get("score", 0.5))
            da      = _domain_authority(r.get("url", ""))
            conf    = round(t_score * da, 4)
            r["_confidence"] = conf
            r["_da"]         = da
            r["_fingerprint"] = _url_fingerprint(r.get("url", ""))
            weighted.append((conf, r))

        ranked = [r for _, r in sorted(weighted, key=lambda x: x[0], reverse=True)]

        # ── 6. Summary synthesis ──────────────────────────────────────
        summary = await self.summarize(topic, ranked, lang=lang)

        # ── 7. Build CitationBundle ───────────────────────────────────
        bundle = self._build_citation_bundle(topic, summary, ranked, len(raw_results))

        # ── 8. Persist to SQL ─────────────────────────────────────────
        await self._persist_insight(session_id, topic, {"summary": summary, "vectors": len(sub_questions)})

        return {
            "message": summary,
            "citations": [s.url for s in bundle.sources],
            "citation_bundle": bundle.model_dump(),
            "data": {
                "sources_raw": len(raw_results),
                "sources_deduped": bundle.deduplicated_sources,
                "v13_trace": True,
            },
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _internal_rag_fallback(self, topic: str, session_id: str, lang: str) -> Dict[str, Any]:
        """PHASE 2: Internal RAG pipeline replacing external search dependencies."""
        # 1. Retrieve from internal knowledge base (FAISS)
        vector_facts = await SovereignVectorStore.search_facts("global", topic, limit=10)
        
        if not vector_facts:
            return {"message": "Internal knowledge base contains no resonance for this topic.", "success": False}
            
        # 2. Synthesize findings
        context = "\n".join([f"- {f.get('fact', '')}" for f in vector_facts])
        summary = await handle_local_sync([
            {"role": "system", "content": "You are the LEVI Internal RAG Synthesizer. Generate a comprehensive report based ONLY on the provided internal knowledge."},
            {"role": "user", "content": f"Topic: '{topic}'\nInternal Data:\n{context}"},
        ], model_type="default")
        
        bundle = self._build_citation_bundle(topic, summary, [], len(vector_facts))
        return {
            "message": summary,
            "citations": ["internal://sovereign-vector-store"],
            "citation_bundle": bundle.model_dump(),
            "data": {
                "sources_deduped": len(vector_facts),
                "rag_fallback_active": True
            }
        }

    def _build_citation_bundle(
        self,
        topic: str,
        summary: str,
        ranked: List[Dict],
        raw_count: int,
    ) -> CitationBundle:
        sources = []
        for r in ranked[:10]:   # top-10 only
            sources.append(CitationSource(
                url=r.get("url", ""),
                title=r.get("title", "Untitled"),
                snippet=r.get("content", "")[:300],
                tavily_score=float(r.get("score", 0.5)),
                domain_authority=float(r.get("_da", 0.5)),
                confidence=float(r.get("_confidence", 0.25)),
                fingerprint=r.get("_fingerprint", ""),
            ))
        return CitationBundle(
            topic=topic,
            summary=summary,
            sources=sources,
            total_sources=raw_count,
            deduplicated_sources=len(ranked),
        )

    async def search(self, query: str, depth: str = "basic", session_id: str = "v13") -> List[Dict[str, Any]]:
        SovereignBroadcaster.broadcast({"type": "AGENT_SEARCH_RESULT", "agent": self.name, "query": query})
        from backend.utils.network import async_safe_request
        try:
            resp = await async_safe_request(
                "POST", 
                "https://api.tavily.com/search", 
                json={
                    "api_key": self.tavily_key, 
                    "query": query, 
                    "search_depth": depth
                }
            )
            data = resp.json()
            return data.get("results", [])
        except Exception as e:
            self.logger.error(f"[ResearchAgent] Search pulse failed: {e}")
            return []

    async def _persist_insight(self, session_id: str, topic: str, data: Dict[str, Any]):
        try:
            from backend.db.postgres_db import get_write_session
            from sqlalchemy import text
            async with get_write_session() as session:
                await session.execute(
                    text("INSERT INTO agent_insights (session_id, agent_id, topic, data, tag) VALUES (:sid, :aid, :top, :data, 'discovery')"),
                    {"sid": session_id, "aid": self.name, "top": topic, "data": json.dumps(data)},
                )
        except Exception as e:
            logger.error("[Research-v13.1] SQL Insight failure: %s", e)

    async def summarize(self, topic: str, results: List[Dict], lang: str = "en") -> str:
        context = "\n".join([
            f"### {r.get('title')} [conf={r.get('_confidence', '?')}]\n"
            f"Source: {r.get('url')}\nContent: {r.get('content', '')[:500]}"
            for r in results[:5]
        ])
        return await handle_local_sync([
            {"role": "system", "content": "You are the LEVI v13 Research Architect."},
            {"role": "user", "content": f"Synthesise v13 report on: {topic}\n\n{context}"},
        ], model_type="default")

    async def _generate_sub_queries(self, topic: str, results: List[Dict]) -> List[str]:
        raw = await handle_local_sync([
            {"role": "system", "content": "You are the LEVI v13 Research Architect."},
            {"role": "user", "content": f"Topic: '{topic}'\nIdentify 2 sub-questions."},
        ], model_type="default")
        return [q.strip() for q in raw.split("\n") if q.strip() and "?" in q][:2]
