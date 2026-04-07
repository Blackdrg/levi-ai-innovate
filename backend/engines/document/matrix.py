"""
backend/engines/document/matrix.py

Sovereign Document Matrix for LEVI OS v7.
High-fidelity RAG via FAISS and Semantic Clustering.
"""

import logging
from typing import Dict, Any
from backend.utils.vector_db import VectorDB
from backend.generation import generate_chat_response

logger = logging.getLogger(__name__)

class DocumentMatrix:
    """
    Handles retrieval and synthesis of content from local user documents.
    """
    
    @staticmethod
    async def retrieve_context(query: str, user_id: str, context: Dict[str, Any]) -> str:
        """
        1. Access the User Matrix (FAISS collection).
        2. Perform Semantic Search with Score Hardening.
        3. Synthesize context into a clean response for the Brain.
        """
        logger.info(f"[DocumentMatrix] Searching for: '{query[:30]}...'")
        
        # We leverage the hardened v6 VectorDB as the raw retrieval layer.
        vdb = await VectorDB.get_user_collection(user_id, name="documents")
        results = await vdb.search(query, limit=5, min_score=0.45)
        
        if not results:
            return "No relevant document context found."

        context_text = "\n\n".join([f"Source: {r.get('filename')}\n{r.get('text')}" for r in results])
        
        system_prompt = (
            "You are the LEVI Document Matrix. Answer ONLY based on the context provided. "
            "If the answer isn't there, admit it. Cite sources clearly."
        )
        
        return await generate_chat_response(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {query}"}
            ],
            model="llama-3.1-8b-instant"
        )
