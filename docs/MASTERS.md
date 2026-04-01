# 👑 LEVI-AI Masters of the Architecture

This document explicitly defines the **Non-Negotiable Immutable Laws** of Sovereign OS v7. If you are extending functionality, you MUST obey these constraints or risk shattering the load balancer.

## Law 1: API Route Immobility
**No file in `backend/api/` may ever process CPU-bound logic.**
FastAPI runs natively async. Processing a Regex block, parsing a massive PDF, or rendering an image inside `api/main.py` blocks the Python Event Loop for ALL global users simultaneously.
- **Enforcement:** If logic takes > 10ms, it is relegated to `engines/` or `services/`.
- **Enforcement:** If logic involves Disk I/O or Hardware (FFmpeg), it MUST be shipped to Celery via `task.delay()`.

## Law 2: The Redis Atom
**No financial unit (Tokens, AI Credits, Tiers) changes without a Redis Lua Lock.**
If an API accepts a Razorpay webhook, it first verifies `is_locked("credits_uid")`. Never execute a sequence like `val = read() -> val = val - 1 -> write(val)` in python natively.

## Law 3: Modularity or Death
**Never `import backend.X`**. The entire migration to v7 relied on killing root-level files.
- You must always path precisely: `from backend.db.firestore_db import db`.
- Never weave the UI directly into backend API schemas.

## Law 4: FAISS Sovereignty
Memory buffers dictate LLM accuracy. When tweaking thresholds (`0.92`), recognize that lowering the threshold forces LEVI into hallucinatory loops blending irrelevant philosophical concepts, while raising it forces total amnesia.
