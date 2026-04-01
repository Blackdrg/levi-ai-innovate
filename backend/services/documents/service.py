import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from backend.utils.vector_db import VectorDB

logger = logging.getLogger(__name__)

class DocumentService:
    """
    Handles ingestion of PDF, DOCX, and TXT files.
    Extracts text, chunks it, and indexes via FAISS.
    """
    
    @classmethod
    async def process_file(cls, file_path: str, user_id: str, filename: str) -> str:
        """
        Main entry point for file processing.
        """
        ext = os.path.splitext(file_path)[1].lower()
        text = ""
        
        try:
            if ext == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            elif ext == ".pdf":
                text = await cls._extract_pdf(file_path)
            elif ext == ".docx":
                text = await cls._extract_docx(file_path)
            else:
                raise ValueError(f"Unsupported extension: {ext}")
            
            if not text:
                raise ValueError("No text extracted from file.")
            
            # 1. Chunking
            chunks = cls._chunk_text(text)
            
            # 2. Vector Indexing
            db = await VectorDB.get_collection(f"docs_{user_id}")
            
            metadatas = [
                {"user_id": user_id, "filename": filename, "chunk_index": i, "total_chunks": len(chunks)}
                for i in range(len(chunks))
            ]
            
            await db.add(chunks, metadatas)
            
            return f"Processed {filename} into {len(chunks)} fragments."
            
        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}")
            raise

    @classmethod
    async def _extract_pdf(cls, path: str) -> str:
        try:
            import PyPDF2  # type: ignore
            text = ""
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except ImportError:
            logger.warning("PyPDF2 not installed. Skipping PDF extraction.")
            return "[Error: PDF support not installed]"

    @classmethod
    async def _extract_docx(cls, path: str) -> str:
        try:
            import docx # type: ignore
            doc = docx.Document(path)
            return "\n".join([p.text for p in doc.paragraphs])
        except ImportError:
            logger.warning("python-docx not installed. Skipping DOCX extraction.")
            return "[Error: DOCX support not installed]"

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Splits text into overlapping chunks for better retrieval (LEVI-AI Standard).
        """
        chunks = []
        if not text: return []
        
        # Ensure we don't have an infinite loop if overlap >= chunk_size
        step = max(1, chunk_size - overlap)
        
        for i in range(0, len(text), step):
            chunks.append(text[i:i + chunk_size])
            
        return chunks

    @classmethod
    async def query_documents(cls, user_id: str, query: str, limit: int = 3) -> str:
        """
        Searches the user's indexed documents for relevant fragments.
        """
        db = await VectorDB.get_collection(f"docs_{user_id}")
        results = await db.search(query, limit=limit)
        
        if not results:
            return ""
        
        context_parts = []
        for r in results:
            context_parts.append(f"From {r.get('filename', 'Unknown')}: {r.get('text', '')}")
            
        return "\n\n".join(context_parts)
