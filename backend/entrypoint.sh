#!/bin/bash
# Exit on error
set -e

# Run migrations (Safe to run multiple times)
echo "Running database migrations..."
alembic upgrade head || echo "Migrations failed, continuing..."

# Seed database if needed
echo "Seeding database..."
python seed.py || echo "Seeding failed or already seeded, continuing..."

# Start Celery worker and beat in the background
# (In production, consider using a process manager like supervisord or separate containers)
echo "Starting Celery worker and beat..."
celery -A backend.tasks worker --loglevel=info --detach
celery -A backend.tasks beat --loglevel=info --detach

# Start the application
echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-10000}" --workers 1
