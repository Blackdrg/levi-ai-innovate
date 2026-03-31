# pyright: reportMissingImports=false
"""
gateway.py (DEPRECATED)

This entry point has been consolidated into backend/main.py as part of the v6 
'Functional Heart' unification. All production infrastructure and modular 
routers are now served directly from main.py.

DEPRECATION NOTICE:
- Use `uvicorn main:app` instead of `uvicorn gateway:app`.
- This file is kept only for legacy deployment compatibility and will be 
  removed in future iterations.
"""

import warnings
from backend.main import app, lifespan

warnings.warn(
    "gateway.py is deprecated and retired. Use backend.main instead.",
    DeprecationWarning,
    stacklevel=2
)

# For compatibility with legacy uvicorn/gunicorn commands
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
