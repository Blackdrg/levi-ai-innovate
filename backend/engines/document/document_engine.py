import logging
import os
from typing import List, Dict, Any, Optional
import numpy as np
import faiss
from backend.engines.base import EngineBase
from backend.engines.utils.security import SovereignSecurity
from backend.embeddings import embed_text

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
        self.index = None
        self.id_map = {} # Map index ID to text fragment
        self._initialize_index()

    def _initialize_index(self):
        """Initializes a FAISS HNSW index for high-speed retrieval."""
        # IndexHNSWFlat: HNSW algorithm on Euclidean distance
        dimension = 384 # BERT/DistilBERT standard dimension (or whatever embedder uses)
        # Using a small dimension as default, will re-init on first ingest if needed
        self.index = faiss.IndexHNSWFlat(dimension, 32) # M=32 for accuracy/speed balance
        self.index.hnsw.efConstruction = 40
        self.index.hnsw.efSearch = 16

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
        Retrieves contextually relevant document fragments using FAISS HNSW.
        """
        self.logger.info(f"Extracting document context for {user_id}")
        
        if self.index.ntotal == 0:
            return []

        try:
            # Generate embedding for the query
            query_emb = await embed_text([query])
            query_vector = np.array(query_emb).astype('float32')
            
            # Perform search
            distances, indices = self.index.search(query_vector, top_k)
            
            hits = []
            for idx in indices[0]:
                if idx != -1 and idx in self.id_map:
                    hits.append(self.id_map[idx])
            
            return hits
        except Exception as e:
            self.logger.error(f"[DocumentEngine] Search failure: {e}")
            return []

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
            
            # Vectorize and add to FAISS
            embeddings = await embed_text(chunks)
            vectors = np.array(embeddings).astype('float32')
            
            # Re-initialize index if dimension mismatch
            if self.index.d != vectors.shape[1]:
                self.index = faiss.IndexHNSWFlat(vectors.shape[1], 32)
                self.id_map = {}
                
            start_id = self.index.ntotal
            self.index.add(vectors)
            
            for i, chunk in enumerate(chunks):
                self.id_map[start_id + i] = chunk

            self.logger.info(f"Ingested {len(chunks)} chunks from {file_path} into FAISS (Total: {self.index.ntotal})")
            
            return {
                "status": "ingested",
                "chunks": len(chunks),
                "total_index_size": self.index.ntotal,
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
