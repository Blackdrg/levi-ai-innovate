@echo off
REM push_graduation.bat — LEVI-AI Sovereign Sync (v13.1.0+)
setlocal enabledelayedexpansion

echo "[🚀] Initializing Sovereign Sync (v13.1.0+)..."

REM 1. Detect Branch
for /f "tokens=*" %%i in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%i
echo "[📍] Current Branch: %BRANCH%"

REM 2. Pulse Pull (Pull FIRST to avoid index errors)
echo "[📡] Pulling latest swarm metadata..."
git pull origin %BRANCH% --rebase --autostash
if %errorlevel% neq 0 (
    echo "[⚠️] Pull failed or requires manual merge. Continuing..."
)

REM 3. Stage & Commit
echo "[🏗️] Staging Graduation Artifacts & Consolidated Reports..."
git add .
echo "[🧱] Committing Graduation Finality..."
git commit -m "🚀 Final Sync: Consolidated Graduation Master Report v13.1.0"

REM 4. Tagging
echo "[🏷️] Refreshing release tag v13.1.0-stable..."
git tag -f v13.1.0-stable -m "Graduation Tier: Absolute Monolith Stable"

REM 5. Secure Force Push
echo "[🛰️] Pushing to Sovereign Hub (%BRANCH%) with Force-Tags..."
git push origin %BRANCH% --tags --force
if %errorlevel% neq 0 (
    echo "[ERROR] Push failed. Check remote connectivity or credentials."
    pause
    exit /b %errorlevel%
)

echo.
echo "[🎓] MASTER SYNC COMPLETE. GRADUATION DOCUMENTS DISTRIBUTED."
echo.
pause
