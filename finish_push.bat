@echo off
echo 🚀 LEVI-AI v4.5 OMNIPRESENT — Global Launch Sync
echo ------------------------------------------------
echo [1/3] Staging all 45 phases of architectural updates...
git add .
if %errorlevel% neq 0 (
    echo [ERROR] git add . failed.
    pause
    exit /b
)

echo [2/3] Committing the architectural sign-off...
git commit -m "feat: LEVI-AI v4.5 Omnipresent — Global Pulse & Live Telemetry"
if %errorlevel% neq 0 (
    echo [WARNING] git commit failed (maybe no changes?). Continuing to push...
)

echo [3/3] Synchronizing with GitHub (Branch: master)...
git push origin master
if %errorlevel% neq 0 (
    echo [ERROR] git push failed. Attempting alternate branch (main)...
    git push origin main
)

if %errorlevel% neq 0 (
    echo [CRITICAL] Push failed on both master and main. Please check Internet or GitHub permissions.
    pause
    exit /b
)

echo 🌌 LEVI-AI v4.5 Global Launch Successful!
pause
