#!/bin/bash
# worker_entrypoint.sh
set -e

echo "=== LEVI Celery Worker Startup ==="

# 1. Start a dummy HTTP server in the background for Cloud Run health checks
# Cloud Run requires a listening port.
python3 -m http.server "${PORT:-8080}" &
HTTP_PID=$!

# 2. Start Celery worker
echo "Starting Celery worker (pool=threads)..."
celery -A celery_app worker --loglevel=info --pool=threads --concurrency="${CELERY_CONCURRENCY:-4}"

# Cleanup
kill $HTTP_PID
