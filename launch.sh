#!/bin/bash
# LEVI-AI Sovereign OS v14.0.0 Launcher
# Engineered for Absolute Autonomy

echo "--------------------------------------------------"
echo "   🧠 LEVI-AI Sovereign OS v9.8.1 Launcher        "
echo "--------------------------------------------------"

# 1. Environment Verification
if [ ! -f .env ]; then
    echo "❌ CRITICAL: .env file missing."
    echo "   Action: Copy .env.example to .env and insert your API keys."
    exit 1
fi

# 2. Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ CRITICAL: Docker not found. Please install Docker & Docker Compose."
    exit 1
fi

# 3. Boot the Sovereign OS
echo "🚀 Booting the Sovereign Fabric (DCN + DBs)..."
docker compose up -d --build

# 4. Final Pulse Check
echo "--------------------------------------------------"
echo "✅ MISSION_ACTIVE: The Sovereign OS is rising."
echo "🔗 API Gateway: http://localhost:8000"
echo "📊 Telemetry: http://localhost:8000/telemetry (Profile: default)"
echo "--------------------------------------------------"
echo "Use 'docker compose logs -f api' to track the Brain Pulse."
