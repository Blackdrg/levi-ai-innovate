"""
backend/services/orchestrator/fusion_engine.py

Sovereign Mind v6.8.8 Fusion Engine.
Synthesizes multiple agent results (Search, Document, Chat) into a single high-fidelity response.
"""

import logging
from typing import List, Dict, Any
from .orchestrator_types import ToolResult
from backend.generation import generate_chat_response

logger = logging.getLogger(__name__)

class FusionEngine:
    @staticmethod
    async def fuse_results(query: str, results: List[ToolResult], context: Dict[str, Any]) -> str:
        """
        Takes multiple agent results and fuses them using a synthesis prompt.
        Prioritizes Local Documents > Web Search > General Chat.
        """
        logger.info(f"[FusionEngine] Fusing results from {len(results)} agents.")
        
        # 1. 📂 Extract facts from each agent
        manifest = []
        for res in results:
            if not res.success: continue
            
            # Formulate a source-aware fact string
            source_tag = f"[{res.agent.upper()}]"
            content = res.message
            manifest.append(f"{source_tag} findings: {content}")

        if not manifest:
            return "The specialized agents were unable to find definitive results for your query."

        # 2. 🧠 Construct Fusion Prompt
        # We use a specialized system prompt for the Llama engine to perform synthesis
        fusion_prompt = f"""
            You are the LEVI-AI Fusion Engine. 
            Objective: Synthesize the findings from multiple specialized agents into a single, high-fidelity response.
            
            USER QUERY: {query}
            
            AGENT FINDINGS:
            {chr(10).join(manifest)}
            
            INSTRUCTIONS:
            1. Resolve any contradictions (Prioritizing DOCUMENT over SEARCH).
            2. Eliminate redundant information.
            3. Maintain a {context.get('mood', 'philosophical')} and sovereign tone.
            4. Cite sources as [Search] or [Document] within the text.
            5. Return ONLY the fused response.
        """

        # 3. ⚡ Execute Synthesis
        messages = [{"role": "system", "content": "You are the Sovereign Synthesizer."}, {"role": "user", "content": fusion_prompt}]
        
        try:
            # We use the standard generation path for the final synthesis
            fused_msg = await generate_chat_response(
                messages=messages,
                model="llama-3.1-8b-instant",
                temperature=0.3 # Low temperature for factual synthesis
            )
            return fused_msg
        except Exception as e:
            logger.error(f"Fusion synthesis failure: {e}")
            # Fallback: Join them with separators
            return "\n\n---\n\n".join([m for m in manifest])

    @staticmethod
    async def fuse_responses(query: str, results: List[ToolResult], context: Dict[str, Any]) -> str:
        """Alias for fuse_results to match legacy calls."""
        return await FusionEngine.fuse_results(query, results, context)
