#!/bin/bash
# scripts/setup-macos.sh
# LEVI-AI Sovereign OS v15.0 GA: macOS Setup Script

set -e

echo "🚀 Starting LEVI-AI macOS Setup..."

# 1. Install Homebrew if missing
if ! command -v brew &> /dev/null; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "✅ Homebrew already installed."
fi

# 2. Install System Dependencies
echo "📦 Installing system dependencies via Homebrew..."
brew update
brew install python@3.10 postgresql@15 redis portaudio git libsndfile

# 3. Start Services
echo "🚀 Starting local services..."
brew services start postgresql@15
brew services start redis

# 4. Environment Setup
echo "🐍 Setting up Python virtual environment..."
python3.10 -m venv venv
source venv/bin/activate

# 5. Dependency Installation
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r backend/requirements.txt

# 6. Check for Apple Silicon (MPS Support)
if [[ $(sysctl -n machdep.cpu.brand_string) == *"Apple"* ]]; then
    echo "🍎 Apple Silicon detected. Installing MPS-optimized torch..."
    pip install torch torchvision torchaudio
else
    echo "💻 Intel Mac detected."
fi

echo "✅ macOS Setup Complete!"
echo "To start LEVI-AI, run: source venv/bin/activate && uvicorn backend.main:app --reload"
