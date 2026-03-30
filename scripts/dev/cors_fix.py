# -----------------------------------------------------------------------
# REPLACE the CORS section in your backend/main.py with this block.
# Find the line: "env_origins = os.getenv("CORS_ORIGINS", "").split(",")"
# and replace everything up to "app.add_middleware(..." with this:
# -----------------------------------------------------------------------
import os  # type: ignore
try:
    from fastapi import FastAPI  # type: ignore
    from fastapi.middleware.cors import CORSMiddleware  # type: ignore
    from backend.main import app  # type: ignore
except ImportError:
    pass

env_origins = os.getenv("CORS_ORIGINS", "").split(",")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    # Vercel domains — add your exact Vercel URL here too
    "https://levi-git-main-daksh-mehats-projects.vercel.app",
    "https://levi-k8iuadcvd-daksh-mehats-projects.vercel.app",
    "https://levi-ai.vercel.app",
]

# Accept any extra origins from environment variable
for o in env_origins:
    origin = o.strip()
    if origin and origin not in origins:
        origins.append(origin)

# If CORS_ORIGINS="*" is set in Render env vars, allow all origins
allow_all = os.getenv("CORS_ORIGINS", "").strip() == "*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else origins,
    allow_credentials=False,   # Must be False when allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
