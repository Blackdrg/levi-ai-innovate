#!/usr/bin/env bash

# push_fixes.sh — run this from the root of your LEVI repo

# Usage: bash push_fixes.sh

set -e



echo "=== LEVI — Pushing all fixes to GitHub ==="



# 1. Make sure we're in a git repo

if [ ! -d ".git" ]; then

  echo "ERROR: Run this script from the root of your LEVI git repository."

  exit 1

fi



# 2. Stage all changed files

git add \

  backend/main.py \

  backend/models.py \

  backend/seed.py \

  backend/embeddings.py \

  backend/auth.py \

  backend/generation.py \

  backend/image_gen.py \

  backend/redis_client.py \

  backend/requirements.txt \

  backend/Dockerfile.prod \

  Dockerfile \

  render.yaml \

  frontend/js/api.js



# 3. Commit

git commit -m "fix: pin transformers<5.0 and all production-readiness patches



- requirements.txt: pin transformers>=4.40.0,<5.0.0 — v5 removed

  pipeline from top-level, crashing startup on Render

- generation.py: lazy pipeline import inside thread with try/except —

  app starts even if model load fails, falls back to curated quotes

- main.py: register RateLimitExceeded handler (429 not 500), async

  image generation via ThreadPoolExecutor, fix startup import paths,

  add search_mode to /health response

- models.py: add UniqueConstraint on Quote.text for safe upsert

- seed.py: replace db.merge() with existence-check upsert — no more

  duplicate quotes on re-deploy

- embeddings.py: expose HAS_MODEL flag, deterministic hash-seeded

  fallback vector (same text = same vector), thread-safe model load

- auth.py: remove broken @app decorator (NameError on import fixed),

  now pure utility module; all routes stay in main.py

- image_gen.py: documented as synchronous/blocking — caller must use

  run_in_executor (done in main.py)

- redis_client.py: export HAS_REDIS and REDIS_URL for startup logging

- Dockerfile / Dockerfile.prod: explicit python:3.11-slim (fixes

  PyTorch / sentence-transformers on Python 3.14)

- render.yaml: healthCheckPath set to /health

- frontend/js/api.js: removed duplicate getAnalytics export"



# 4. Push

git push origin main



echo ""

echo "=== Done! ==="

echo "Render will auto-deploy. Watch logs at: https://dashboard.render.com"

echo ""

echo "Expected in new logs:"

echo "  transformers-4.x.x installed (NOT 5.x)"

echo "  Redis connected"

echo "  Application startup complete."

echo "  Your service is live"