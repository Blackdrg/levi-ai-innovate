import logging
import asyncio
from typing import Dict, Any, List, Optional
from backend.engines.chat.generation import SovereignGenerator
from backend.services.search.service import SearchService
from backend.services.memory.vault import MemoryVault

logger = logging.getLogger(__name__)

class KnowledgeNexus:
    """
    Sovereign OS v8.8: KnowledgeNexus cross-referencing engine.
    Audits internal memory against live global knowledge to prevent hallucination drift.
    """
    def __init__(self):
        self.generator = SovereignGenerator()
        self.search_service = SearchService()
        self.memory_vault = MemoryVault()

    async def audit_fact(self, claim: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs a high-fidelity audit of a specific claim.
        Returns a consensus report with a 'groundedness' score.
        """
        logger.info(f"[KnowledgeNexus] Auditing claim: {claim[:100]}...")

        # 1. Parallel Retrieval: Memory + Live Search
        memory_task = self.memory_vault.search(claim, limit=3)
        search_task = self.search_service.search(claim, num_results=3)
        
        memory_results, search_results = await asyncio.gather(memory_task, search_task)

        # 2. Consensus Synthesis
        audit_report = await self._synthesize_consensus(claim, memory_results, search_results, context)

        # 3. Decision Gating
        is_grounded = audit_report.get("grounding_score", 0.0) >= 0.75
        
        return {
            "claim": claim,
            "grounded": is_grounded,
            "report": audit_report,
            "sources": {
                "memory_count": len(memory_results),
                "web_count": len(search_results)
            }
        }

    async def _synthesize_consensus(self, claim: str, memory: List[Any], web: List[Any], context: Optional[str]) -> Dict[str, Any]:
        """Uses the Council of Models to resolve contradictions between memory and web results."""
        prompt = (
            f"CLAIM TO AUDIT: {claim}\n\n"
            f"CONTEXT: {context or 'None'}\n\n"
            "INTERNAL MEMORY FINDINGS:\n" + "\n".join([str(m) for m in memory]) + "\n\n"
            "LIVE WEB RESULTS:\n" + "\n".join([str(w) for w in web]) + "\n\n"
            "TASK: Reconcile these findings. If memory contradicts live results, prioritize live results for volatile facts.\n"
            "Respond in JSON: {'grounding_score': 0.0, 'contradictions': [], 'final_verdict': '', 'reasoning': ''}"
        )

        res_raw = await self.generator.council_of_models([
            {"role": "system", "content": "You are the LEVI KnowledgeNexus Auditor. Resolution and high-fidelity grounding are your core directives."},
            {"role": "user", "content": prompt}
        ], temperature=0.1)

        try:
            import json
            return json.loads(res_raw.strip().replace("```json", "").replace("```", ""))
        except:
            logger.warning("[KnowledgeNexus] Failed to parse synthesis JSON. Falling back to safe defaults.")
            return {"grounding_score": 0.5, "contradictions": ["Parsing error during audit"], "final_verdict": "Inconclusive"}

knowledge_nexus = KnowledgeNexus()
