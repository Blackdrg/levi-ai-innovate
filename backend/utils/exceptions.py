# backend/utils/exceptions.py
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime

class LEVIException(Exception):
    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR", metadata: dict = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.metadata = metadata or {}
        super().__init__(self.message)

class SovereignError(LEVIException):
    """Raised when the Local Sovereign Engine fails or is unavailable."""
    def __init__(self, message: str, metadata: dict = None):
        super().__init__(message, status_code=503, error_code="SOVEREIGN_ENGINE_OFFLINE", metadata=metadata)

class ResourceSaturationError(LEVIException):
    """Raised when the monolith's 8Gi RAM or Concurrency Gate is saturated."""
    def __init__(self, message: str):
        super().__init__(message, status_code=429, error_code="MONOLITH_SATURATED")

def levi_exception_handler(request_id: str, exc: LEVIException):
    content = {
        "error": exc.message,
        "error_code": exc.error_code,
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    if exc.metadata:
        content["metadata"] = exc.metadata
        
    return JSONResponse(status_code=exc.status_code, content=content)
