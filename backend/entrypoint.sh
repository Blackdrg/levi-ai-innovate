#!/bin/bash
# Exit on error
set -e

# Run migrations (Safe to run multiple times)
echo "Running database migrations..."
alembic upgrade head || echo "Migrations failed, continuing..."

# Seed database if needed
echo "Seeding database..."
python seed.py || echo "Seeding failed or already seeded, continuing..."

# Note: Celery worker and beat are managed separately (e.g., in render.yaml or docker-compose)
# to avoid orphaned processes and duplicate execution.

# Start the application
echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-10000}" --workers 1
