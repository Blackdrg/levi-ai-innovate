import logging
import asyncio
import numpy as np
from typing import List, Dict, Any
from backend.engines.base import EngineBase
from backend.engines.utils.security import SovereignSecurity

logger = logging.getLogger(__name__)

class SearchEngine(EngineBase):
    """
    Sovereign Search & Retrieval Hub.
    Combines Local RAG (FAISS) with Global Web Pulse (Tavily/DDG).
    """
    
    def __init__(self):
        super().__init__("Search")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")

    async def _run(self, query: str, mode: str = "hybrid", **kwargs) -> Any:
        """
        Executes a search mission. v15.0 GA: Local-First Priority.
        """
        safe_query = SovereignSecurity.mask_pii(query)
        self.logger.info(f"Initiating Search: {safe_query} [{mode}]")
        
        results = {"local": [], "web": [], "summary": ""}

        # 1. ALWAYS TRY LOCAL FIRST
        if mode in ["hybrid", "local"]:
            local_data = await self._local_search(safe_query)
            results["local"] = local_data.get("local", [])

        # 2. STEP 3.3/3.4: CALCULATE CONFIDENCE & DECIDE ON WEB PULSE
        local_confidence = len(results["local"]) / 5.0 # Simple heuristic
        
        if mode in ["hybrid", "web"] and local_confidence < 0.6:
            self.logger.info(f"[Search] Local hits sparse ({local_confidence:.1f}). Engaging Global Web Pulse...")
            web_data = await self._web_search(safe_query)
            results["web"] = web_data.get("web", [])
        else:
            self.logger.info(f"🎯 [Search] Local knowledge sufficient ({local_confidence:.1f}). Skipping web dependency.")

        results["summary"] = self._synthesize_search_results(results)
        return results

    async def _local_search(self, query: str) -> Dict[str, List[Dict]]:
        """Dense vector search on the Sovereign local index."""
        try:
            # Bridging to legacy vector store for transition period
            from backend.db.vector_store import vector_index, embed_text
            query_vector = np.array([embed_text(query)])
            D, I = vector_index.search(query_vector, k=5)
            
            hits = []
            for i, idx in enumerate(I[0]):
                if idx != -1:
                    hits.append({
                        "id": int(idx),
                        "score": float(D[0][i]),
                        "source": "sovereign_local",
                        "content": f"(Retrieved Sovereign Segment {idx})"
                    })
            return {"local": hits}
        except Exception as e:
            self.logger.error(f"Local search failure: {e}")
            return {"local": []}

    async def _web_search(self, query: str) -> Dict[str, List[Dict]]:
        """Global Web Pulse via Tavily or DDG."""
        if not self.tavily_api_key:
            return {"web": []}
            
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=self.tavily_api_key)
            # Run blocking client in executor
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: client.search(query=query, search_depth="balanced"))
            
            return {"web": resp.get("results", [])}
        except Exception as e:
            self.logger.warning(f"Web search failure: {e}")
            return {"web": []}

    def _synthesize_search_results(self, results: Dict) -> str:
        """Creates a readable summary of search findings."""
        summary = []
        if results["local"]:
            summary.append(f"Found {len(results['local'])} matches in Sovereign Knowledge Base.")
        if results["web"]:
            summary.append(f"Retrieved {len(results['web'])} insights from the Global Web Pulse.")
        
        if not summary:
            return "No external data detected."
        return " | ".join(summary)

    async def hybrid_search(self, **kwargs) -> str:
        """Compatibility wrapper for simple string output."""
        result = await self.execute(**kwargs)
        return result.data["summary"] if result.status == "success" else "Search mission failed."
