#!/bin/bash
# LEVI-AI Sovereign OS v14.0.0: One-Click Private Deploy
# "Sovereignty is not a gift, but a deterministic infrastructure."

echo "🛡️ Initiating Sovereign Deployment Phase (Sovereign OS v14.0.0)..."

# 1. Environment Check
if ! [ -x "$(command -v docker)" ]; then
  echo 'Error: docker is not installed. Technical Finality requires Docker.' >&2
  exit 1
fi

if ! [ -x "$(command -v docker-compose)" ]; then
  echo 'Error: docker-compose is not installed.' >&2
  exit 1
fi

# 2. Config Resonance
if [ ! -f .env ]; then
    echo "📋 Manifest .env missing. Synchronizing from .env.example..."
    cp .env.example .env
    # Generate unique keys
    sed -i "s/graduated_v14_resonance/$(openssl rand -hex 16)/g" .env
    echo "✅ Logic-Before-Language: .env synchronized."
else
    echo "✅ Logic-Before-Language: .env pulse detected."
fi

# 3. Pulling Collective Intelligence
echo "📡 Pulling Sovereign Images..."
docker-compose pull

# 4. Neural Link Ignition
echo "🚀 Igniting Sovereign OS Swarm..."
docker-compose up -d --build

# 5. Health Audit
echo "🧪 Auditing System Integrity..."
sleep 5
STATUS=$(curl -s http://localhost:8000/ | grep -o "online")

if [ "$STATUS" == "online" ]; then
    echo "🏁 GRADUATION REACHED. LEVI-AI Sovereign OS is now pulsing at http://localhost:8000"
else
    echo "⚠️ Resonance Drift detected. Check logs with 'docker-compose logs -f'"
fi
