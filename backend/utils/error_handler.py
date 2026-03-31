"""
backend/utils/error_handler.py

Global exception handling and error response standardization.
Maps internal exceptions to user-friendly HTTP responses with error codes.
"""

import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from .exceptions import LEVIException

logger = logging.getLogger(__name__)

async def levi_exception_handler(request: Request, exc: LEVIException):
    """
    Standardized handler for LEVI-specific exceptions.
    """
    logger.error(
        "LEVI Error [%s]: %s (Path: %s)",
        exc.error_code, exc.message, request.url.path
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "error_code": exc.error_code,
            "status": "error"
        }
    )

async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unhandled internal exceptions.
    Prevents leaking internal stack traces in production.
    """
    logger.critical(
        "Unhandled Exception: %s (Path: %s)",
        str(exc), request.url.path, exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER__ERROR,
        content={
            "error": True,
            "message": "A disturbance in the cosmic field occurred.",
            "error_code": "INTERNAL_SERVER_ERROR",
            "status": "critical"
        }
    )
