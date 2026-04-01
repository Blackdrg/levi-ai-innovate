"""
backend/services/orchestrator/agents/document_agent.py

Document Agent for LEVI-AI v6.8.8.
Performs Retrieval-Augmented Generation (RAG) on private user documents.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from backend.utils.vector_db import VectorDB
from backend.generation import generate_chat_response

logger = logging.getLogger(__name__)

class DocumentInput(BaseModel):
    input: str = Field(..., description="The user's question about their documents")
    user_id: str = Field(..., description="User ID for retrieving private collection")
    collection_name: str = Field("documents", description="Target collection name")

class DocumentAgent(BaseTool[DocumentInput, StandardToolOutput]):
    """
    The Document Agent performs RAG using FAISS and private vector storage.
    """
    
    name = "document_agent"
    description = "Performs RAG (Retrieval-Augmented Generation) on user documents."
    input_schema = DocumentInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: DocumentInput, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes document search and contextual generation.
        """
        user_id = input_data.user_id
        query = input_data.input
        
        try:
            # 1. 📂 Get the user's document collection
            vector_db = await VectorDB.get_user_collection(user_id, name=input_data.collection_name)
            
            # 2. 🔍 Search for relevant context
            results = await vector_db.search(query, limit=5, min_score=0.45)
            
            if not results:
                return {
                    "success": True,
                    "message": "I searched through your documents but found no relevant context for this query.",
                    "data": {"results_found": 0}
                }

            # 3. 🧠 Format context for Synthesis
            context_text = "\n\n".join([f"Source: {r.get('filename', 'Unknown')}\nContent: {r.get('text', '')}" for r in results])
            
            system_prompt = (
                "You are the LEVI Document Agent. Your job is to answer questions based ONLY on the provided document context.\n"
                "If the answer is not in the context, state that you don't have enough information from the documents.\n"
                "Be precise, professional, and cite the source filename if available."
            )
            
            prompt = f"Context:\n{context_text}\n\nQuestion: {query}"
            
            # 4. ⚡ Generate synthesis
            response = await generate_chat_response(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.1
            )
            
            return {
                "success": True,
                "message": response,
                "data": {
                    "results_found": len(results),
                    "sources": list(set([r.get("filename") for r in results if r.get("filename")]))
                }
            }

        except Exception as e:
            logger.error(f"[DocumentAgent] failure: {e}")
            return {
                "success": False,
                "error": f"Document system encountered a barrier: {str(e)}",
                "agent": self.name
            }
