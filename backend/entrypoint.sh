# entrypoint.sh — Start server directly for Firestore architecture
set -e

echo "=== LEVI Backend Startup (Gateway Mode) ==="

# 1. Skip Alembic Migrations (Firestore Native)
# Alembic is for SQL-based analytics/legacy DBs which are not used in Cloud Run production.
echo "[1/2] Skipping SQL migrations (Firestore native detected)..."

# 2. Start application via Gateway
echo "[2/2] Starting Uvicorn with Gateway..."
exec uvicorn gateway:app \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --workers 2 \
  --access-log