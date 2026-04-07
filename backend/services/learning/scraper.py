"""
LEVI-AI Knowledge Acquisition Engine v13.0.0.
Absolute Monolith production-grade scraper.
Synchronizes high-fidelity seeds with the Postgres SQL Fabric.
"""

import os
import json
import logging
import arxiv
import fitz  # PyMuPDF
from typing import List, Dict, Any
from backend.db.postgres_db import get_write_session
from sqlalchemy import text

logger = logging.getLogger(__name__)

class ScraperServiceV13:
    """
    Sovereign Knowledge Acquisition Engine (v13.0.0).
    Targets high-fidelity Research/Arxiv/GitHub 'Knowledge Seeds'.
    """
    
    def __init__(self):
        self.arxiv_client = arxiv.Client()

    async def _save_seed(self, source: str, title: str, url: str, content: str, metadata: Dict[str, Any]):
        """Persists knowledge seed into the Absolute Monolith SQL Fabric."""
        try:
            async with get_write_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO knowledge_seeds (source, title, url, content, metadata, resonance_score)
                        VALUES (:src, :title, :url, :content, :meta, :score)
                        ON CONFLICT (url) DO NOTHING
                    """),
                    {
                        "src": source,
                        "title": title,
                        "url": url,
                        "content": content[:10000], # Cap for first-pass resonance
                        "meta": json.dumps(metadata),
                        "score": 0.85 # Initial swarm trust
                    }
                )
        except Exception as e:
            logger.error(f"[KnowledgeEngine-v13] SQL Seed failure: {e}")

    async def scrape_arxiv(self, queries: List[str], max_results: int = 5) -> List[Dict[str, Any]]:
        """Queries Arxiv and distills knowledge from PDF fragments."""
        results = []
        for query in queries:
            logger.info(f"[KnowledgeEngine-v13] Discovering Arxiv: {query}")
            search = arxiv.Search(query=query, max_results=max_results)
            
            for result in self.arxiv_client.results(search):
                try:
                    pdf_path = result.download_pdf(dirpath="/tmp")
                    text_content = ""
                    with fitz.open(pdf_path) as doc:
                        for page in doc: text_content += page.get_text()
                    
                    seed = {
                        "source": "arxiv",
                        "title": result.title,
                        "url": result.entry_id,
                        "content": text_content,
                        "metadata": {"authors": [a.name for a in result.authors]}
                    }
                    await self._save_seed(**seed)
                    results.append(seed)
                    os.remove(pdf_path)
                except Exception as e:
                    logger.error(f"[KnowledgeEngine-v13] Arxiv drift: {e}")
        
        return results

    async def run_cycle(self):
        """Standard Absolute Monolith Knowledge Cycle (v13.0)."""
        logger.info("🧠 Initiating Monolith Knowledge Acquisition (v13.0.0)...")
        phi_queries = ["Stoicism philosophy", "AGI Architecture", "Ethics in Swarms"]
        await self.scrape_arxiv(phi_queries)
        logger.info("[KnowledgeEngine-v13] Resonance Cycle Complete.")

# Singleton graduation
scraper = ScraperServiceV13()
