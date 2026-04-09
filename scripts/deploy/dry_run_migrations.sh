#!/bin/bash
# dry_run_migrations.sh — Alembic validation against an ephemeral Postgres container

set -e

echo "=== LEVI-AI: Alembic Dry Run Validation ==="

# Define ephemeral DB credentials
export DB_USER="dryrun_user"
export DB_PASS="dryrun_pass"
export DB_NAME="dryrun_db"
export DB_PORT="5433" # Use alternate port

# Spin up Ephemeral PostgreSQL Container
echo "[1/4] Spinning up ephemeral PostgreSQL container..."
CONTAINER_ID=$(docker run --name levi-dryrun-db \
  -e POSTGRES_USER=$DB_USER \
  -e POSTGRES_PASSWORD=$DB_PASS \
  -e POSTGRES_DB=$DB_NAME \
  -p $DB_PORT:5432 \
  -d postgres:15-alpine)

echo "Waiting for ephemeral database to become ready..."
sleep 5

# Override the application env to point to ephemeral db
export DATABASE_URL="postgresql+asyncpg://$DB_USER:$DB_PASS@localhost:$DB_PORT/$DB_NAME"

echo "[2/4] Capturing SQL output via Alembic..."
cd backend
alembic upgrade head --sql > ../migration_dry_run.sql
echo "Generated migration script at /migration_dry_run.sql."

echo "[3/4] Running Alembic actual upgrade on ephemeral container..."
if alembic upgrade head; then
    echo "✅ Success: Migrations executed cleanly against ephemeral DB."
else
    echo "❌ ERROR: Migrations failed during runtime validation."
    docker stop $CONTAINER_ID
    docker rm $CONTAINER_ID
    exit 1
fi

echo "[4/4] Teardown ephemeral container..."
cd ..
docker stop $CONTAINER_ID
docker rm $CONTAINER_ID

echo "=== Dry Run Complete ==="
exit 0
