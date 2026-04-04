@echo off
setlocal
echo --------------------------------------------------
echo    🧠 LEVI-AI Sovereign OS v13.0.0 Launcher        
echo    Engineered for Absolute Autonomy (v13.0 Monolith)     
echo --------------------------------------------------

:: 1. Environment Verification
if not exist ".env" (
    echo ❌ ERROR: .env file not found.
    echo    Action: Copy .env.example to .env and insert your API keys.
    pause
    exit /b 1
)

:: 2. Launch the Monolith
echo 🚀 Booting the Sovereign Fabric...
docker-compose up -d --build

:: 3. Final Pulse Check
echo --------------------------------------------------
echo ✅ MISSION_ACTIVE: The Monolith is rising.
echo 🔗 API Gateway: http://localhost:8000
echo 📊 Telemetry: http://localhost:8000/telemetry
echo --------------------------------------------------
echo 🩺 Running Graduation Audit...
python tests/verify_v13_monolith.py

echo Use 'docker-compose logs -f api' to track the v13 Brain Pulse.
pause
