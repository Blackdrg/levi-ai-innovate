# entrypoint.sh — Start server directly for Firestore architecture
set -e

echo "=== LEVI Backend Startup (Firestore Native) ==="

# 1. Start application
echo "[1/1] Starting Uvicorn..."
exec uvicorn main:app \
  --host 0.0.0.0 \
  --port "${PORT:-10000}" \
  --workers 1 \
  --access-log