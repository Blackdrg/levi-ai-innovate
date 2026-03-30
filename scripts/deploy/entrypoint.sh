#!/bin/bash
# entrypoint.sh — run migrations, seed, then start server
set -e

echo "=== LEVI Backend Startup ==="

# 1. Run DB migrations
echo "[1/3] Running Alembic migrations..."
alembic upgrade head || echo "  Migrations failed or already up to date — continuing..."

# 2. Seed initial quote data
echo "[2/3] Seeding database..."
python seed.py || echo "  Seeding skipped (already seeded or failed) — continuing..."

# 3. Start application
echo "[3/3] Starting Uvicorn..."
exec uvicorn main:app \
  --host 0.0.0.0 \
  --port "${PORT:-10000}" \
  --workers 1 \
  --timeout-keep-alive 75 \
  --access-log
