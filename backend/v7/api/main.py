"""
⚠️ [LEGACY_NEUTRALIZED] LEVI-AI Sovereign OS v7.0.
This entry point has been consolidated into the 'Absolute Monolith' v13.0.0.
Redirecting all architectural resonance to: backend.api.main:app
"""

from fastapi import FastAPI, HTTPException

app = FastAPI(title="LEVI-AI Legacy Bridge (v7)", version="NEUTRALIZED")

@app.get("/{full_path:path}")
async def legacy_redirection_notice(full_path: str):
    raise HTTPException(
        status_code=410, 
        detail="Neural link severed. This legacy v7 endpoint has been graduated to the v13.0.0 Absolute Monolith. Please update your neural headers to the /api/v13/ tier."
    )
