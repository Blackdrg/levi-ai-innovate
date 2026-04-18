# backend/api/vault.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List, Dict, Any
import uuid
import time
import os
from backend.auth.logic import get_current_user
from backend.services.knowledge_extractor import KnowledgeExtractor
from backend.services.memory_manager import MemoryManager

router = APIRouter(tags=["Vault"])
extractor = KnowledgeExtractor()
memory = MemoryManager()

# Placeholder for a real document store (e.g. S3/GCS or Local)
DOC_STORE = {}

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), identity: Any = Depends(get_current_user)):
    """
    Sovereign Vault: Secure Document Ingestion.
    Uploads a document, extracts Knowledge Triplets, and indexes it into T3/T4 memory.
    """
    uid = getattr(identity, "uid", "guest")
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    
    content = await file.read()
    # In a real OS, we'd use a PDF parser here (e.g. PyMuPDF or Tika)
    text_content = content.decode('utf-8', errors='ignore')
    
    # 1. Store metadata
    DOC_STORE[doc_id] = {
        "filename": file.filename,
        "size": len(content),
        "owner": uid,
        "timestamp": time.time(),
        "status": "processing"
    }

    # 2. Extract Knowledge Triplets (Async)
    triplets = await extractor.distill_triplets(
        user_input=f"Document: {file.filename}",
        response=text_content[:2000], # Process first 2k chars for now
        tenant_id=uid
    )

    # 3. Index into Memory (T3 Vector + T4 Graph)
    # This would call memory.add_episodic or similar
    
    DOC_STORE[doc_id]["status"] = "indexed"
    DOC_STORE[doc_id]["triplets_count"] = len(triplets)

    return {
        "status": "success",
        "document_id": doc_id,
        "filename": file.filename,
        "triplets_extracted": len(triplets)
    }

@router.get("/list")
async def list_documents(identity: Any = Depends(get_current_user)):
    uid = getattr(identity, "uid", "guest")
    user_docs = [
        {"id": k, **v} for k, v in DOC_STORE.items() if v["owner"] == uid
    ]
    return user_docs

@router.get("/{doc_id}")
async def get_document(doc_id: str, identity: Any = Depends(get_current_user)):
    doc = DOC_STORE.get(doc_id)
    if not doc or doc["owner"] != getattr(identity, "uid", "guest"):
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc
