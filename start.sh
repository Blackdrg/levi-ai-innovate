#!/bin/bash
# LEVI-AI v22.0.0 Sovereign OS: Autonomous-SOVEREIGN - Global Deployment Command
set -e

# Phase 1: Neural Synthesis (Build Frontend)
echo "🧬 Synthesizing Neural Frontend (v22.0.0-GA)..."
cd levi-frontend
if [ ! -d "node_modules" ]; then
    echo "📦 Installing neural dependencies..."
    npm install --silent
fi
echo "🏗️  Building production-grade artifacts..."
npm run build
cd ..

# Phase 2: SQL Resonance (Migrations)
echo "🛡️  Ensuring SQL Fabric Resilience (V22 Graduation)..."
# Ensure the postgres container is running before migration
docker-compose up -d postgres
printf "Waiting for SQL availability..."
until docker-compose exec postgres pg_isready -U levi; do
  printf "."
  sleep 1
done
echo "✅ Resonance Confirmed. Applying v22 migrations..."
docker-compose exec postgres psql -U levi -d levi_db -f /docker-entrypoint-initdb.d/init.sql

# Phase 3: Launch Sovereign Stack
echo "🚀 Terminal Ignition: LEVI-AI v22.0.0-GA GRADUATED"
docker-compose up -d --build

echo "✅ Pulse Active: Sovereign OS v22 GA is operational."
echo "   Gateway:  https://localhost"
echo "   Monitor:  http://localhost:3000"
echo "   Graph:    http://localhost:7474"
echo "   Metrics:  http://localhost:8000/metrics"
