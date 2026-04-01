import os
import shutil
import uuid
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, UploadFile, File, BackgroundTasks
from backend.services.auth.logic import get_current_user_optional
from backend.services.documents.service import DocumentService
from backend.utils.exceptions import LEVIException
from backend.utils.sanitization import sanitize_filename

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Documents"])

UPLOAD_DIR = "backend/data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Ingests PDF, DOCX, or TXT for RAG retrieval.
    """
    user_id = current_user.get("uid") if current_user else f"guest:{request.client.host}"
    
    # 1. Validation
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".pdf", ".docx", ".txt"):
         raise LEVIException(f"Unsupported file type: {ext}. Only PDF, DOCX, TXT allowed.", status_code=400)
    
    # 2. Store temporarily
    safe_name = sanitize_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info("File uploaded: %s (User: %s)", file.filename, user_id)
        
        # 3. Trigger processing in background
        if background_tasks:
            background_tasks.add_task(DocumentService.process_file, file_path, user_id, file.filename)
        else:
            await DocumentService.process_file(file_path, user_id, file.filename)
            
        return {
            "status": "processing",
            "filename": file.filename,
            "message": "Enlightenment process initiated. Your document will be indexed momentarily."
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise LEVIException("The document could not be ingested. Please try again.", status_code=500)
