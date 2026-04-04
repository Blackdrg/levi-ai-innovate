#!/bin/bash
# LEVI-AI v13 Sovereign OS: Absolute Monolith - Global Command
set -e

# Phase 1: Neural Synthesis (Build Frontend)
echo "🧬 Synthesizing Neural Frontend (v13.0)..."
cd levi-frontend
if [ ! -d "node_modules" ]; then
    echo "📦 Installing neural dependencies..."
    npm install
fi
echo "🏗️  Building premium artifacts..."
npm run build
cd ..

# Phase 2: SQL Resonance (Migrations)
echo "🛡️  Ensuring SQL Fabric Resilience..."
# Ensure the postgres container is running before migration
docker-compose up -d postgres
printf "Waiting for SQL availability..."
until docker-compose exec postgres pg_isready -U levi; do
  printf "."
  sleep 1
done
echo "✅ Resonance Confirmed. Applying v13 migrations..."
docker-compose exec postgres psql -U levi -d levi_db -f /docker-entrypoint-initdb.d/init.sql

# Phase 3: Launch Sovereign Stack
echo "🚀 Terminal Ignition: LEVI-AI v13.0 Absolute Monolith"
docker-compose up -d --build

echo "✅ Pulse Active: Sovereign OS is operational."
echo "   Gateway:  https://localhost"
echo "   Monitor:  http://localhost:3000"
echo "   Graph:    http://localhost:7474"
