import os
import httpx
import logging
from typing import Dict, Any
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from backend.generation import _async_call_llm_api
from backend.payments import use_credits
from backend.utils.network import async_safe_request, ai_service_breaker

logger = logging.getLogger(__name__)

class SearchInput(BaseModel):
    input: str = Field(..., description="The search query or topic to research")
    user_id: str = "guest"
    user_tier: str = "free"

class SearchAgent(BaseTool[SearchInput, StandardToolOutput]):
    name = "search_agent"
    description = "Real-time thematic researcher. Fetches factual and historical insights from the web."
    input_schema = SearchInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: SearchInput, context: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Credit Enforcement
        if input_data.user_id and not input_data.user_id.startswith("guest:"):
            try:
                use_credits(str(input_data.user_id), 1)
            except Exception as e:
                return {"success": False, "error": f"Insufficient credits: {str(e)}", "agent": self.name}

        # 2. Resilient Tavily Integration
        tavily_key = os.getenv("TAVILY_API_KEY")
        if tavily_key:
            try:
                logger.info(f"[SearchAgent] Performing live search for: {input_data.input}")
                response = await ai_service_breaker.async_call(
                    async_safe_request,
                    "POST", 
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key,
                        "query": input_data.input,
                        "search_depth": "advanced" if input_data.user_tier != "free" else "basic",
                        "include_answer": True,
                        "max_results": 5
                    }
                )
                data = response.json()
                
                # Use Tavily's generated answer if available, else summarize results
                search_answer = data.get("answer")
                if not search_answer and data.get("results"):
                    summaries = [f"- {r['title']}: {r['content'][:250]}" for r in data["results"][:3]]
                    search_answer = "Found the following insights:\n" + "\n".join(summaries)
                
                if search_answer:
                    return {
                        "success": True,
                        "message": search_answer,
                        "data": {"raw_results": data.get("results", [])},
                        "agent": self.name
                    }
            except Exception as e:
                logger.warning(f"[SearchAgent] Tavily search failed: {e}. Falling back to LLM researcher.")

        # 3. Fallback: LLM-based Factual Research
        logger.info(f"[SearchAgent] Using LLM Fallback for: {input_data.input}")
        system_prompt = (
            "You are the LEVI Search Engine. Provide 3-5 concise, deep, and factual insights "
            "about the topic. Focus on historical context, scientific facts, or philosophical depth. "
            "Be precise and informative. Format as plain text with bullet points."
        )

        llm_response = await _async_call_llm_api(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Topic: {input_data.input}"}
            ],
            model="llama-3.1-8b-instant",
            provider="groq"
        )
        
        return {
            "success": True,
            "message": llm_response or "The collective knowledge is silent on this matter.",
            "data": {"source": "llm_fallback"},
            "agent": self.name
        }
