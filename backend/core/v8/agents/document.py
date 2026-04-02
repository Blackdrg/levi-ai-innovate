import logging
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from .base import BaseV8Agent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class DocumentInput(BaseModel):
    input: str = Field(..., description="The user's question about their documents")
    user_id: str = "guest"

class DocumentAgentV8(BaseV8Agent[DocumentInput]):
    """
    LeviBrain v8: Document Intelligence System
    RAG + Re-ranking + Synthesis
    """

    def __init__(self):
        super().__init__("DocumentAgentV8")
        self.generator = SovereignGenerator()

    async def _execute_system(self, input_data: DocumentInput, context: Dict[str, Any]) -> AgentResult:
        query = input_data.input
        user_id = input_data.user_id
        self.logger.info(f"[Document-V8] starting system operation for {user_id}")

        # 1. Retrieval: Initial RAG pass
        from backend.engines.document.document_engine import DocumentEngine
        doc_engine = DocumentEngine()
        fragments = await doc_engine.extract_context(query=query, user_id=user_id, top_k=15)
        
        if not fragments:
            return AgentResult(success=True, message="No relevant documents found in the Sovereign archive.")

        # 2. Re-ranker: Score fragments for precision
        ranked_fragments = await self._rerank_fragments(query, fragments)
        
        # 3. Summarizer: Contextual synthesis
        final_answer = await self._synthesize_answer(query, ranked_fragments)
        
        return AgentResult(
            success=True,
            message=final_answer,
            data={
                "fragments_retrieved": len(fragments),
                "fragments_used": len(ranked_fragments),
                "components": ["RAG", "Re-ranker", "Synthesizer"]
            }
        )

    async def _rerank_fragments(self, query: str, fragments: List[str]) -> List[str]:
        """Re-ranker system pass."""
        # LLM based scoring for the most relevant context
        context_preview = "\n".join([f"ID: {i} | Content: {f[:200]}..." for i, f in enumerate(fragments)])
        
        rerank_prompt = (
            f"Query: {query}\n"
            f"Context Fragments:\n{context_preview}\n\n"
            "Score each fragment for relevance (0.0-1.0). Return ONLY the top 5 IDs in order of importance."
            "\nOutput JSON: {\"top_ids\": [0, 5, 2]}"
        )
        
        try:
            raw_res = await self.generator.council_of_models([
                {"role": "system", "content": "You are the LEVI Context Scorer."},
                {"role": "user", "content": rerank_prompt}
            ])
            import json
            import re
            json_match = re.search(r"\{.*\}", raw_res, re.DOTALL)
            if json_match:
                 data = json.loads(json_match.group(0))
                 top_ids = data.get("top_ids", [])
                 return [fragments[i] for i in top_ids if i < len(fragments)]
        except Exception as e:
            self.logger.warning(f"Re-ranking failed: {e}")
            
        return fragments[:5] # Fallback

    async def _synthesize_answer(self, query: str, fragments: List[str]) -> str:
        """Synthesis pass."""
        context_text = "\n\n".join(fragments)
        
        prompt = (
            f"Question: {query}\n\n"
            f"Context:\n{context_text}\n\n"
            "Answer precisely based ONLY on the context. Use citations [1], [2] etc."
        )
        
        return await self.generator.council_of_models([
            {"role": "system", "content": "You are the LEVI Document Sage."},
            {"role": "user", "content": prompt}
        ])
