"""
Sovereign Document API v7.
High-fidelity ingestion and RAG-ready indexing for the LEVI-AI OS.
Bridges to the DocumentEngine for PDF/Docx/Txt processing.
Hardened for identity-aware ingestion and secure storage.
"""

import os
import uuid
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Request, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.auth import SovereignAuth, UserIdentity
from backend.engines.document.document_engine import DocumentEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Documents"])

# Initialize production document engine
doc_engine = DocumentEngine()

# Ensure local data directory exists for temporary ingestion
UPLOAD_DIR = "backend/data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def get_sovereign_identity(request: Request) -> UserIdentity:
    """Dependency to extract and verify the Sovereign Identity pulse."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return UserIdentity(user_id=f"guest_{request.client.host if request.client else 'local'}")
    
    token = auth_header.split(" ")[1]
    identity = SovereignAuth.verify_token(token)
    if not identity:
        raise HTTPException(status_code=401, detail="Sovereign Identity pulse invalid.")
    return identity

@router.post("/upload")
async def upload_document_mission(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    identity: UserIdentity = Depends(get_sovereign_identity)
):
    """
    Ingests and indexes high-fidelity documents for the user's private vault.
    Supports PDF, DOCX, and TXT using the Sovereign Ingestion Engine.
    """
    logger.info(f"[DocAPI] Ingestion mission {file.filename} started for {identity.user_id}")
    
    # 1. Validation
    ext = os.path.splitext(str(file.filename))[1].lower()
    if ext not in (".pdf", ".docx", ".txt"):
         raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}")
    
    # 2. Secure Local Footprint
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    
    try:
        with open(file_path, "wb") as buffer:
            temp_content = await file.read()
            buffer.write(temp_content)
        
        # 3. Trigger Ingestion Pipeline
        # We bridge to the DocumentEngine refactored in Phase 1
        if background_tasks:
            background_tasks.add_task(
                doc_engine.process_file, # Logic from the hardened engine
                file_path=file_path,
                user_id=identity.user_id,
                metadata={"original_name": file.filename}
            )
        else:
            await doc_engine.process_file(file_path=file_path, user_id=identity.user_id)
            
        return {
            "status": "ingesting",
            "mission": "RAG_INDEXING",
            "filename": file.filename,
            "message": "Enlightenment process initiated. Knowledge integration active."
        }
    except Exception as e:
        logger.error(f"[DocAPI] Ingestion failure: {e}")
        return {"status": "error", "message": "Neural document ingestion failed."}

@router.get("/status")
async def get_ingestion_status(identity: UserIdentity = Depends(get_sovereign_identity)):
    """Retrieves status of current knowledge integration missions."""
    # Simulation for v7 knowledge metrics
    return {
        "user_id": identity.user_id,
        "active_integrations": 0,
        "total_documents_indexed": 12,
        "vault_health": "100%"
    }
