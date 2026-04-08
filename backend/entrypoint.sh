#!/bin/bash
# entrypoint.sh — Start server directly for Firestore architecture
set -e

echo "=== LEVI Backend Startup (Gateway Mode) ==="

if [ "${SKIP_MIGRATIONS:-false}" = "true" ]; then
  echo "[1/2] Skipping Alembic migrations (SKIP_MIGRATIONS=true)..."
else
  echo "[1/2] Running Alembic migrations..."
  alembic -c backend/alembic.ini upgrade head
fi

echo "[2/2] Starting Uvicorn with Gateway..."
exec uvicorn backend.api.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --workers "${WORKERS:-1}" \
  --log-level info
