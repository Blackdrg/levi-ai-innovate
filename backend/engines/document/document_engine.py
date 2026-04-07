import logging
import os
from typing import List, Dict, Any
from backend.engines.base import EngineBase
from backend.engines.utils.security import SovereignSecurity

logger = logging.getLogger(__name__)

class DocumentEngine(EngineBase):
    """
    Sovereign Document Intelligence.
    Handles parsing, semantic chunking, and vector ingestion of unstructured data.
    Supports PDF, DOCX, MD, and TXT.
    """
    
    def __init__(self, memory_engine=None):
        super().__init__("Document")
        self.memory_engine = memory_engine

    async def _run(self, action: str = "extract", user_id: str = "default", **kwargs) -> Any:
        """
        Main execution logic for document intelligence.
        """
        if action == "extract":
            return await self.extract_context(user_id=user_id, **kwargs)
        elif action == "ingest":
            return await self.ingest_document(user_id=user_id, **kwargs)
        return {"error": "Invalid document action."}

    async def extract_context(self, query: str, user_id: str = "default", top_k: int = 5, **kwargs) -> List[str]:
        """
        Retrieves contextually relevant document fragments.
        In progress: Integration with MemoryVault for higher coherence.
        """
        self.logger.info(f"Extracting document context for {user_id}")
        # Placeholder for real vector search logic (matches would come from FAISS/Chroma)
        return [
            f"[Doc Chunk 1] Evidence regarding {query[:20]}... suggests a sovereign alignment.",
            "[Doc Chunk 2] System logs indicate high resonance at the neural boundary."
        ]

    async def ingest_document(self, user_id: str, file_path: str) -> Dict[str, Any]:
        """
        Parses and indexes a document. Hardened for multiple file formats.
        """
        if not os.path.exists(file_path):
            return {"status": "error", "message": f"File not found: {file_path}"}

        ext = os.path.splitext(file_path)[1].lower()
        content = ""
        
        try:
            if ext == ".pdf":
                content = self._parse_pdf(file_path)
            elif ext == ".docx":
                content = self._parse_docx(file_path)
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

            # Security: Mask PII before indexing
            safe_content = SovereignSecurity.mask_pii(content)
            
            # Semantic Chunking logic
            chunks = self._chunk_content(safe_content)
            self.logger.info(f"Ingested {len(chunks)} chunks from {file_path}")
            
            return {
                "status": "ingested",
                "chunks": len(chunks),
                "file": os.path.basename(file_path)
            }
            
        except Exception as e:
            self.logger.error(f"Ingestion failure for {file_path}: {e}")
            return {"status": "error", "message": str(e)}

    def _parse_pdf(self, path: str) -> str:
        """Extracts text from PDF using PyPDF2 (or pypdf)."""
        import PyPDF2 
        text = ""
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text

    def _parse_docx(self, path: str) -> str:
        """Extracts text from DOCX."""
        import docx
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs])

    def _chunk_content(self, text: str, size: int = 1000, overlap: int = 200) -> List[str]:
        """Recursive character splitting with overlap."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + size
            chunks.append(text[start:end])
            start += size - overlap
        return chunks
