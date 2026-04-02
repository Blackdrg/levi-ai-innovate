import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.core.agent_base import SovereignAgent, AgentResult
from backend.engines.document.document_engine import DocumentEngine as DocEngineCore
from backend.engines.chat.generation import SovereignGenerator

logger = logging.getLogger(__name__)

class DocumentInput(BaseModel):
    input: str = Field(..., description="The user's question about their documents")
    user_id: str = "guest"
    collection_name: str = "documents"

class DocumentAgent(SovereignAgent[DocumentInput, AgentResult]):
    """
    Sovereign Document Agent (DocumentArchitect).
    Specializes in Retrieval-Augmented Generation (RAG) on private datasets.
    """
    
    def __init__(self):
        super().__init__("DocumentArchitect")

    async def _run(self, input_data: DocumentInput, lang: str = "en", **kwargs) -> Dict[str, Any]:
        """
        Retrieval Protocol v7:
        1. Multi-step Semantic Extraction.
        2. Contextual Fusion & Relevance Analysis.
        3. Council-based RAG Synthesis (High-Fidelity).
        """
        user_id = input_data.user_id
        query = input_data.input
        self.logger.info(f"RAG Mission for {user_id}: '{query[:40]}'")
        
        # Initialize Document Engine per mission
        from backend.engines.document.document_engine import DocumentEngine
        doc_engine = DocumentEngine()
        
        # 1. Semantic Context Extraction
        context_fragments = await doc_engine.extract_context(
            query=query, 
            user_id=user_id,
            top_k=8
        )
        
        if not context_fragments:
            return {
                "message": "I searched the Sovereign archive but no relevant context was found.",
                "success": True
            }

        # 2. Contextual Fusion
        context_text = "\n\n".join(context_fragments)
        
        # 3. Final Sovereign RAG Synthesis
        system_prompt = (
            "You are the LEVI Document Agent. Your job is to answer questions based ONLY on the provided context.\n"
            "Technical Requirements:\n"
            "- Integrity: If the answer is not in context, state it clearly.\n"
            "- Precision: Cite sources precisely using [Source X] format.\n"
            "- Tone: Professional, insight-driven, and philosophical.\n"
        )
        
        generator = SovereignGenerator()
        
        # Use the council for rigorous retrieval synthesis
        final_response = await generator.council_of_models([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {context_text}\n\nQuestion: {query}"}
        ])

        return {
            "message": final_response,
            "data": {
                "fragments_retrieved": len(context_fragments),
                "collection": input_data.collection_name
            }
        }
