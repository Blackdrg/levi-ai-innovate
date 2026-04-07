import logging
from typing import Dict, Any
from pydantic import BaseModel, Field
from backend.core.agent_base import SovereignAgent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class SearchInput(BaseModel):
    input: str = Field(..., description="The search query or topic to research")
    user_id: str = "guest"
    mode: str = "hybrid"

class SearchAgent(SovereignAgent[SearchInput, AgentResult]):
    """
    Sovereign Search Agent (SearchNavigator).
    Specializes in real-time thematic research and fact-finding.
    """
    
    def __init__(self):
        super().__init__("SearchNavigator")

    async def _run(self, input_data: SearchInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Discovery Protocol v7:
        1. Hybrid Search Execution (Local + Web).
        2. Relevance Analysis & Pulse Extraction.
        3. Council-based Insight Synthesis (High-Fidelity).
        """
        query = input_data.input
        self.logger.info(f"Navigating the Pulse: '{query[:40]}'")
        
        # Engage the Search Engine bridge
        from backend.engines.search.search_engine import SearchEngine
        search_engine = SearchEngine()
        
        # 1. Search Logic Execution
        search_data = await search_engine.execute(
            query=query, 
            mode=input_data.mode
        )
        
        if search_data.status != "success":
            return {"message": "Search Navigation interrupted by Pulse anomaly.", "success": False}

        results = search_data.data
        summary = results.get("summary", "No factual pulses detected.")
        
        # 2. Final Sovereign Search Synthesis
        generator = SovereignGenerator()
        system_prompt = (
            "You are the LEVI Search Navigator. Your role is to provide real-time factual insights.\n"
            "Technical Requirements:\n"
            "- Integrity: Use provided search summary to construct authoritative responses.\n"
            "- Precision: Cite key factual claims.\n"
            "- Resilience: If no data exists, admit it gracefully.\n"
        )
        
        # Engage the council for factual grounding
        # We use the core SovereignGenerator council
        final_response = await generator.council_of_models([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Search Data Summary: {summary}\n\nSearch Question: {query}"}
        ])

        return {
            "message": final_response,
            "data": {
                "local_hits": len(results.get("local", [])),
                "web_hits": len(results.get("web", [])),
                "mode": input_data.mode,
                "confidence": search_data.confidence
            }
        }
