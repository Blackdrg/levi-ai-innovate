# backend/agents/scout_agent.py
import logging
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.agents.base import SovereignAgent, AgentResult
from backend.memory.vector_store import SovereignVectorStore

logger = logging.getLogger(__name__)

class ScoutInput(BaseModel):
    query: str
    deep_search: bool = False
    session_id: str

class ScoutAgent(SovereignAgent[ScoutInput, AgentResult]):
    """
    Sovereign Phase 2: The Scout.
    Specialist in reconnaissance, local web crawling, and knowledge harvesting.
    """
    def __init__(self):
        super().__init__(name="Scout", profile="Reconnaissance Specialist")

    async def _run(self, input_data: ScoutInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        logger.info(f"[Scout] Discovery mission initiated: {input_data.query}")
        user_id = kwargs.get("user_id", "default")
        
        urls_to_crawl = []
        
        # 1. Determine if query is a direct URL or search term
        if input_data.query.startswith("http://") or input_data.query.startswith("https://"):
            urls_to_crawl.append(input_data.query)
        else:
            # Use search engine to find target URLs
            from backend.engines.search.search_engine import SearchEngine
            search = SearchEngine()
            external_context = await search.search(input_data.query, deep=input_data.deep_search)
            for res in external_context.get("results", [])[:3]: # Cap at top 3 for speed
                if res.get("url"):
                    urls_to_crawl.append(res.get("url"))
        
        scraped_data = []
        
        # 2. Phase 2.3: Local Web Crawler (Parallel Execution)
        if urls_to_crawl:
            self.logger.info(f"[Scout] Crawling {len(urls_to_crawl)} URLs locally...")
            crawl_tasks = [self._crawl_url(url) for url in urls_to_crawl]
            scraped_results = await asyncio.gather(*crawl_tasks)
            
            for i, content in enumerate(scraped_results):
                if content:
                    url = urls_to_crawl[i]
                    scraped_data.append({"url": url, "content": content[:2000]}) # Truncate for processing
                    
                    # 3. Phase 2.1 & 2.4: Store in Internal Knowledge Base with Domain Authority
                    authority_score = self._calculate_domain_authority(url)
                    await SovereignVectorStore.store_fact(
                        user_id=user_id,
                        fact=f"Source [{url}]: {content[:1500]}",
                        category="scraped_web_data",
                        importance=authority_score
                    )

        # 4. Memory Recon (Internal Context)
        from backend.engines.memory.memory_engine import MemoryEngine
        memory = MemoryEngine()
        internal_context = await memory.execute(query=input_data.query, user_id=user_id)
        
        # 5. Consolidation
        findings = {
            "internal": internal_context.get("data", []),
            "scraped_web": scraped_data,
            "total_signals": len(internal_context.get("data", [])) + len(scraped_data)
        }
        
        message = f"Scout mission successful. Crawled {len(scraped_data)} sites and crystallized findings into the Internal Knowledge Base."
        
        return {
            "success": True,
            "message": message,
            "data": findings,
            "confidence": 0.95,
            "citations": urls_to_crawl
        }

    async def _crawl_url(self, url: str) -> Optional[str]:
        """Local Web Crawler implementation using aiohttp and BeautifulSoup."""
        try:
            headers = {"User-Agent": "LEVI-AI ScoutAgent/15.0 (Sovereign Web Crawler)"}
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")
                        for element in soup(["script", "style", "nav", "footer", "header"]):
                            element.extract()
                        return soup.get_text(separator=' ', strip=True)
                    else:
                        self.logger.warning(f"[Scout] Failed to crawl {url} (Status: {response.status})")
                        return None
        except Exception as e:
            self.logger.error(f"[Scout] Crawl error on {url}: {e}")
            return None

    def _calculate_domain_authority(self, url: str) -> float:
        """Phase 2.4: Domain Authority Engine"""
        try:
            domain = urlparse(url).netloc.lower()
            if domain.endswith(".gov"): return 0.95
            if domain.endswith(".edu"): return 0.85
            if "docs." in domain: return 0.80
            if domain.endswith(".org"): return 0.70
            return 0.50
        except:
            return 0.50
