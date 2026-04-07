import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from .base import BaseV8Agent, AgentResult
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class DocumentInput(BaseModel):
    input: str = Field(..., description="The user's question about their documents")
    user_id: str = "guest"

class FragmentModel(BaseModel):
    content: str
    score: float = 0.0
    source_id: Optional[str] = None

class DocumentData(BaseModel):
    query: str
    fragments: List[FragmentModel]
    total_retrieved: int
    precision_layer: str = "ContextScorer-v8"

class DocumentAgentV8(BaseV8Agent[DocumentInput]):
    """
    LeviBrain v8: Document Intelligence System
    RAG + Re-ranking + Data Extraction
    """

    def __init__(self):
        super().__init__("DocumentAgentV8")
        self.generator = SovereignGenerator()

    async def _execute_system(self, input_data: DocumentInput, context: Dict[str, Any]) -> AgentResult[DocumentData]:
        query = input_data.input
        user_id = input_data.user_id
        self.logger.info(f"[Document-V8] Initiating structured audit for {user_id}")

        # 1. Retrieval: Multi-vector RAG pass
        from backend.engines.document.document_engine import DocumentEngine
        doc_engine = DocumentEngine()
        fragments = await doc_engine.extract_context(query=query, user_id=user_id, top_k=15)
        
        if not fragments:
            return AgentResult(
                success=True, 
                message="No relevant documentation was discovered in the Sovereign archives.",
                data=DocumentData(query=query, fragments=[], total_retrieved=0)
            )

        # 2. Re-ranker: Precision Scoring (Pass 1)
        ranked_fragments = await self._rerank_fragments(query, fragments)
        
        # 3. Model mapping
        structured_fragments = [
            FragmentModel(content=f, score=0.9) # Simple score for now
            for f in ranked_fragments
        ]

        return AgentResult(
            success=True,
            message=f"Document intelligence extraction complete. {len(structured_fragments)} relevant fragments identified.",
            data=DocumentData(
                query=query,
                fragments=structured_fragments,
                total_retrieved=len(fragments)
            )
        )

    async def _rerank_fragments(self, query: str, fragments: List[str]) -> List[str]:
        """Precision re-ranking pass using internal ContextScorer."""
        context_preview = "\n".join([f"Fragment [{i}]: {f[:250]}..." for i, f in enumerate(fragments)])
        
        rerank_prompt = (
            f"QUERY: {query}\n"
            f"SOURCE DATA:\n{context_preview}\n\n"
            "Task: Score each fragment for relevance and factual grounding (0.0-1.0).\n"
            "Return JSON: {\"top_ids\": [idx1, idx2, ...], \"scores\": [0.95, 0.88, ...]}"
        )
        
        try:
            raw_res = await self.generator.council_of_models([
                {"role": "system", "content": "You are the LEVI Context Scorer."},
                {"role": "user", "content": rerank_prompt}
            ])
            import json as json_lib
            import re
            match = re.search(r"\{.*\}", raw_res, re.DOTALL)
            if match:
                 data = json_lib.loads(match.group(0))
                 top_ids = data.get("top_ids", [])
                 # Return top 6 fragments
                 return [fragments[i] for i in top_ids if i < len(fragments)][:6]
        except Exception as e:
            self.logger.warning(f"Precision re-ranking failed: {e}")
            
        return fragments[:5] # Fallback to standard top-k

