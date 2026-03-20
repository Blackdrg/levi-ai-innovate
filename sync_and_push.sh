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
git add .

# 3. Commit with definitive message
echo "Committing changes..."
git commit -m "fix: memory optimization for Render free tier

- embeddings.py: lazy load sentence-transformers, skip on Render
- generation.py: lazy load distilgpt2, skip on Render, use API fallback
- render.yaml: ensure WEB_CONCURRENCY=1 and RENDER=true
- Dockerfile.prod: explicitly use --workers 1
- seed.py: existence-check upsert to prevent duplicate quotes" || echo "No new changes to commit"



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