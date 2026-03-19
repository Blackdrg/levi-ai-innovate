#!/usr/bin/env bash

# sync_and_push.sh — definitive sync for LEVI production readiness

set -e



echo "=== LEVI — Synchronizing all production files to GitHub ==="



# 1. Verify Git

if [ ! -d ".git" ]; then

  echo "ERROR: Run this script from the root of your LEVI repository."

  exit 1

fi



# 2. Stage all production-critical files

echo "Staging files..."

git add \

  main.py \

  backend/main.py \

  backend/models.py \

  backend/db.py \

  backend/seed.py \

  backend/embeddings.py \

  backend/generation.py \

  backend/image_gen.py \

  backend/redis_client.py \

  backend/requirements.txt \

  backend/Dockerfile.prod \

  Dockerfile \

  render.yaml \

  frontend/js/api.js \

  sync_and_push.sh



# 3. Commit with definitive message

echo "Committing changes..."

git commit -m "fix: definitive production sync



- main.py (root): add entrypoint proxy for Render/Vercel

- models.py: added FeedItem model and UniqueConstraint on Quote.text

- requirements.txt: pinned transformers<5.0 and bcrypt<5.0 for stability

- main.py (backend): removed module-level pwd_context.hash and fixed imports

- generation.py: background model loading with rule-based fallback

- seed.py: existence-check upsert to prevent duplicate quotes

- redis_client.py: implemented caching and conversation persistence

- render.yaml: healthCheckPath set to /health" || echo "No new changes to commit"



# 4. Push to main

echo "Pushing to GitHub (main branch)..."

git push origin main



echo ""

echo "=== Done! ==="

echo "Render will auto-deploy. Watch logs at: https://dashboard.render.com"

echo ""

echo "Expected in new logs:"

echo "  ✅ Redis connected"

echo "  ✅ Database tables ready"

echo "  ✅ Application startup complete"

echo "  ✅ Your service is live 🎉"