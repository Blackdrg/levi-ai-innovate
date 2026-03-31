import logging
from typing import Dict, Any
from pydantic import BaseModel, Field
from ..tool_base import BaseTool, StandardToolOutput
from backend.services.documents.service import DocumentService

logger = logging.getLogger(__name__)

class DocumentInput(BaseModel):
    query: str = Field(..., description="The query to ask from the user documents")
    user_id: str = "guest"

class DocumentAgent(BaseTool[DocumentInput, StandardToolOutput]):
    name = "document_agent"
    description = "Internal knowledge retriever. Use this for 'ask from document' queries."
    input_schema = DocumentInput
    output_schema = StandardToolOutput

    async def _run(self, input_data: DocumentInput, context: Dict[str, Any]) -> Dict[str, Any]:
        user_id = input_data.user_id
        query = input_data.query
        
        logger.info(f"[DocumentAgent] Querying documents for {user_id}: {query}")
        
        try:
            # 1. Search Vector DB
            relevant_context = await DocumentService.query_documents(user_id, query)
            
            if not relevant_context:
                return {
                    "success": True,
                    "message": "I searched the internal records but found no relevant fragments.",
                    "data": {"found": False},
                    "agent": self.name
                }
            
            # 2. Return findings for synthesis
            return {
                "success": True,
                "message": f"Relevant findings from your documents:\n\n{relevant_context}",
                "data": {"found": True, "context": relevant_context},
                "agent": self.name
            }
            
        except Exception as e:
            logger.error(f"[DocumentAgent] Error: {e}")
            return {
                "success": False,
                "error": f"Internal document retrieval failed: {str(e)}",
                "agent": self.name
            }
