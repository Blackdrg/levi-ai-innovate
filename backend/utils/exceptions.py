# backend/utils/exceptions.py
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime

class LEVIException(Exception):
    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

def levi_exception_handler(request_id: str, exc: LEVIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
