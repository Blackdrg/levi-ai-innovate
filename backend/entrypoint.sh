# entrypoint.sh — Start server directly for Firestore architecture
set -e

echo "=== LEVI Backend Startup (Firestore Native) ==="

# 1. Apply Migrations (Analytics/Legacy DB)
echo "[1/2] Applying database migrations..."
alembic upgrade head || echo "WARNING: Alembic migration failed, continuing..."

# 2. Start application
echo "[2/2] Starting Uvicorn..."
exec uvicorn main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --workers 1 \
  --access-log