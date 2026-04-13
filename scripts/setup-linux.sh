#!/bin/bash
# scripts/setup-linux.sh
# LEVI-AI Sovereign OS v15.0 GA: Linux Setup Script

set -e

echo "🚀 Starting LEVI-AI Linux Setup..."

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
else
    echo "❌ Could not detect OS. Please install manually."
    exit 1
fi

echo "💻 Detected OS: $OS"

if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    echo "📦 Ubuntu/Debian detected. Installing dependencies..."
    sudo apt-get update
    sudo apt-get install -y python3.10 python3.10-venv python3-pip \
        postgresql postgresql-contrib \
        redis-server \
        docker.io \
        docker-compose \
        portaudio19-dev \
        libsndfile1
elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Fedora"* ]]; then
    echo "📦 RHEL-based OS detected. Installing dependencies..."
    sudo yum install -y python3.10 postgresql-server redis docker
    sudo systemctl enable --now postgresql
else
    echo "⚠️ OS not explicitly supported by this script. Attempting generic install..."
fi

# CUDA Setup (Optional check)
if command -v nvidia-smi &> /dev/null; then
    echo "🎮 NVIDIA GPU detected. Ensure CUDA toolkit is installed for best performance."
fi

# 1. Environment Setup
echo "🐍 Setting up Python virtual environment..."
python3.10 -m venv venv
source venv/bin/activate

# 2. Dependency Installation
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r backend/requirements.txt

# 3. Service Management
echo "🚀 Starting local services..."
if command -v systemctl &> /dev/null; then
    sudo systemctl start postgresql
    sudo systemctl start redis-server
else
    sudo service postgresql start
    sudo service redis-server start
fi

echo "✅ Linux Setup Complete!"
echo "To start LEVI-AI, run: source venv/bin/activate && uvicorn backend.main:app --host 0.0.0.0 --port 8000"
