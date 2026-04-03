import os
import logging
import asyncio
import aiohttp
import arxiv
import fitz  # PyMuPDF
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class ScraperService:
    """
    Autonomous Scraper Service for Phase 6: Unbound Training Array.
    Targeting high-fidelity Philosophical and Architectural data.
    """
    
    def __init__(self, storage_dir: str = "backend/data/training_raw"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.arxiv_client = arxiv.Client()

    async def scrape_arxiv(self, queries: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Queries Arxiv and extracts full-text from PDFs.
        """
        results = []
        for query in queries:
            logger.info(f"[Scraper] Searching Arxiv for: {query}")
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            for result in self.arxiv_client.results(search):
                try:
                    # Download PDF
                    pdf_path = result.download_pdf(dirpath=str(self.storage_dir))
                    text = self._extract_text_from_pdf(pdf_path)
                    
                    results.append({
                        "source": "arxiv",
                        "title": result.title,
                        "url": result.entry_id,
                        "published": result.published.isoformat(),
                        "content": text,
                        "metadata": {
                            "authors": [a.name for a in result.authors],
                            "summary": result.summary
                        }
                    })
                    # Clean up PDF to save space after extraction
                    os.remove(pdf_path)
                except Exception as e:
                    logger.error(f"[Scraper] Failed to process Arxiv result {result.entry_id}: {e}")
        
        return results

    async def scrape_github(self, queries: List[str], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Scrapes READMEs and core code files from trending GitHub repositories.
        Using public Search API (unauthenticated for now, limited).
        """
        results = []
        async with aiohttp.ClientSession() as session:
            for query in queries:
                logger.info(f"[Scraper] Searching GitHub for: {query}")
                search_url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page={limit}"
                headers = {"Accept": "application/vnd.github.v3+json"}
                
                async with session.get(search_url, headers=headers) as resp:
                    if resp.status != 200:
                        logger.warning(f"[Scraper] GitHub search failed: {resp.status}")
                        continue
                    
                    data = await resp.json()
                    for repo in data.get("items", []):
                        repo_name = repo["full_name"]
                        # Fetch README
                        readme_url = f"https://api.github.com/repos/{repo_name}/readme"
                        async with session.get(readme_url, headers=headers) as r_resp:
                            if r_resp.status == 200:
                                r_data = await r_resp.json()
                                download_url = r_data.get("download_url")
                                if download_url:
                                    async with session.get(download_url) as content_resp:
                                        content = await content_resp.text()
                                        results.append({
                                            "source": "github",
                                            "title": repo_name,
                                            "url": repo["html_url"],
                                            "content": content,
                                            "metadata": {
                                                "stars": repo["stargazers_count"],
                                                "description": repo["description"]
                                            }
                                        })
        return results

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Helper to extract clean text from PDF using PyMuPDF."""
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text

    async def run_cycle(self):
        """Standard Unbound Scraper Cycle."""
        phi_queries = [
            "Stoicism philosophy", 
            "Marcus Aurelius Meditations", 
            "Existentialism AGI",
            "Information theory of consciousness",
            "Post-human ethics",
            "Spinoza Ethica"
        ]
        tech_queries = [
            "Self-improving AI architecture", 
            "Neural Symbolic reasoning", 
            "Autonomous Agent Swarms",
            "Recursive neural tensor networks",
            "Complexity theory"
        ]
        
        # Phase 1: Scraping (Simultaneous)
        results = await asyncio.gather(
            self.scrape_arxiv(phi_queries, max_results=15),
            self.scrape_github(tech_queries, limit=5)
        )
        
        # Flatten results
        all_content = [item for sublist in results for item in sublist]
        logger.info(f"[Scraper] Cycle complete. Harvested {len(all_content)} data seeds.")
        return all_content

# Singleton instance
scraper = ScraperService()
