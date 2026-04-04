#!/bin/bash
# LEVI-AI v13 Sovereign OS: Global Build & Pulse Sequence
set -e

echo "🚀 Initiating Phase 2: Frontend Synthesis..."
cd levi-frontend
if [ ! -d "node_modules" ]; then
  echo "📦 Installing neural dependencies..."
  npm install
fi
echo "🏗️  Building premium static artifacts..."
npm run build
cd ..

echo "🧬 Phase 3: Infrastructure Localization..."
# Ensure any C:\ legacy data is safely ignored or pointed to D:\
# The Docker Desktop engine will handle the volume mounts from the D drive workspace.

echo "🐳 Phase 4: Containerized Cognition..."
# Note: Ensure certs exist for Nginx SSL before this step
# openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -sha256 -days 365 -nodes -subj "/C=XX/ST=State/L=City/O=Organization/OU=Unit/CN=localhost" || true

docker compose up -d --build

echo "✅ Pulse Active: Sovereign OS v13.0 is operational."
echo "   Gateway:  https://localhost"
echo "   Monitor:  http://localhost:3000"
echo "   Graph:    http://localhost:7474"
