#!/bin/bash
# Exit on error
set -e

# Run migrations/seeding if needed
echo "Seeding database..."
python seed.py || echo "Seeding failed or already seeded, continuing..."

# Start the application
echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1
