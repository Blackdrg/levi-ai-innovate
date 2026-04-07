import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

logger = logging.getLogger(__name__)

class SovereignVersionMiddleware(BaseHTTPMiddleware):
    """
    Sovereign API Versioning Middleware v13.0.0.
    Handles X-API-Version headers and enforces deprecation policies.
    """
    
    CURRENT_VERSION = "v1"
    DEPRECATED_VERSIONS = ["v0", "beta"]
    SUNSET_DATE = "2026-12-31"

    async def dispatch(self, request: Request, call_next):
        # 1. Version Detection
        # We assume the version is in the path /api/v1/...
        path = request.url.path
        version = "v1" # Default
        
        if path.startswith("/api/"):
            parts = path.split("/")
            if len(parts) > 2 and parts[2].startswith("v"):
                version = parts[2]

        # 2. Deprecation Handling
        if version in self.DEPRECATED_VERSIONS:
            logger.warning(f"[Versioning] Deprecated API call: {version} from {request.client.host if request.client else 'unknown'}")
            
        # 3. Process Request
        response: Response = await call_next(request)
        
        # 4. Inject Versioning Headers (v13.0 Standards)
        response.headers["Sovereign-API-Version"] = version
        response.headers["Sovereign-Current-Stable"] = self.CURRENT_VERSION
        
        if version in self.DEPRECATED_VERSIONS:
            response.headers["Warning"] = f'299 - "This API version ({version}) is deprecated and will be sunset on {self.SUNSET_DATE}"'
            response.headers["Sunset"] = self.SUNSET_DATE

        return response
