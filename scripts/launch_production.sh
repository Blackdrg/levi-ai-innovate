#!/bin/bash
# Sovereign AI Production Launcher (v14.0)
# Final Wiring & Deployment Synthesis

set -e

echo "🛡️  LEVI-AI Sovereign OS: Production Initialization..."

# 1. Environment Synthesis
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Synthesizing from .env.production..."
    cp .env.production .env
fi

# 2. Command Calibration (V1 vs V2 Resilience)
if docker compose version >/dev/null 2>&1; then
    DOCKER_CMD="docker compose"
elif docker-compose --version >/dev/null 2>&1; then
    DOCKER_CMD="docker-compose"
else
    echo "❌  Neither 'docker compose' nor 'docker-compose' is functional in this environment."
    echo "💡  Please ensure Docker Desktop is running and WSL Integration is enabled for this distro."
    exit 1
fi

echo "🐳  Using Command: $DOCKER_CMD"

# 3. Certificate Synthesis (Self-Signed for testing api/app domains)
mkdir -p certs
if [ ! -f certs/cert.pem ]; then
    echo "🔐  Generating Sovereign SSL/TLS Certificates..."
    openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem \
        -days 365 -nodes -subj "/C=US/ST=Sovereign/L=Monolith/O=LEVI-AI/CN=*.levi-ai.com"
fi

# 3. Directory Synthesis
mkdir -p data/ollama data/postgres data/redis data/neo4j vault/backups logs

# 5. Pull Cognitive Weights
echo "🧠  Warming up Local LLM (Ollama)..."
$DOCKER_CMD up -d ollama
$DOCKER_CMD run --rm ollama-init

# 6. Full Orchestration
echo "🚀  Launching LEVI-AI Sovereign Stack (v14.0)..."
$DOCKER_CMD up -d --build

# 6. Health Audit
echo "🧪  Waiting for API Resonance..."
until curl -s -f http://api.levi-ai.com/api/v1/health > /dev/null; do
    echo -n "."
    sleep 2
done

echo -e "\n✅  Graduation Complete. Sovereign OS is ACTIVE."
echo "🌍  Frontend: https://app.levi-ai.com"
echo "📡  API:      https://api.levi-ai.com"
echo "📊  Metrics:  http://localhost:3000 (Grafana)"
