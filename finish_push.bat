@echo off
echo 🚀 LEVI-AI v4.5 OMNIPRESENT — Global Launch Sync
echo ------------------------------------------------

echo [1/4] Building Frontend Optimized Assets (CSS)...
cd frontend
call npm install
call npm run build
cd ..
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed. Please check frontend/ package dependencies.
    pause
    exit /b
)

echo [2/4] Staging all architectural updates (Backend + Frontend)...
git add .
if %errorlevel% neq 0 (
    echo [ERROR] git add . failed.
    pause
    exit /b
)

echo [3/4] Committing the architectural sign-off (Phase 2 Fixes)...
git commit -m "fix: critical pre-launch fixes — chat router, firebase config, json-logger, auth-race"
if %errorlevel% neq 0 (
    echo [WARNING] git commit failed (maybe no changes?). Continuing to push...
)

echo [4/4] Synchronizing with GitHub (Branch: master)...
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

echo 🌌 LEVI-AI v4.5 Global Launch Initiated!
echo Check your Actions tab at: https://github.com/Blackdrg/LEVI-AI/actions
pause
