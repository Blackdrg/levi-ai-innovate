#!/usr/bin/env bash

# sync_and_push.sh â€” definitive sync for LEVI production readiness

set -e



echo "=== LEVI â€” Synchronizing all production files to GitHub ==="



# 1. Verify Git

if [ ! -d ".git" ]; then

  echo "ERROR: Run this script from the root of your LEVI repository."

  exit 1

fi



# 2. Stage all production-critical files

echo "Staging files..."

git add \

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

  push_fixes.sh



# 3. Commit with definitive message

echo "Committing changes..."

git commit -m "fix: definitive production sync



- models.py: added FeedItem model and UniqueConstraint on Quote.text

- requirements.txt: pinned transformers<5.0 and bcrypt<5.0 for stability

- main.py: removed module-level pwd_context.hash and fixed imports

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

echo "  âœ… Redis connected"

echo "  âœ… Database tables ready"

echo "  âœ… Application startup complete"

echo "  âœ… Your service is live ðŸŽ‰"