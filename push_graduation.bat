@echo off
REM push_graduation.bat — LEVI-AI Sovereign Sync (v13.1.0+)
setlocal enabledelayedexpansion

echo [🚀] Initializing Sovereign Sync (v13.1.0+)...

REM 1. Detect Branch
for /f "tokens=*" %%i in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%i
echo [📍] Current Branch: %BRANCH%

REM 2. Stage Changes
echo [🏗️] Staging Graduation Artifacts & Consolidated Reports...
git add .

REM 3. Pulse Pull (Avoid non-fast-forward)
echo [📡] Pulling latest swarm metadata...
git pull origin %BRANCH% --rebase

REM 4. Sovereign Commit
echo [🧱] Committing Graduation Finality & Master Sync...
git commit -m "🚀 Final Sync: Consolidated Graduation Master Report v13.1.0"

REM 5. Tagging (Update v13.1.0-stable to latest)
echo [🏷️] Refreshing release tag v13.1.0-stable...
git tag -f v13.1.0-stable -m "Graduation Tier: Absolute Monolith Stable"

REM 6. Secure Push
echo [🛰️] Pushing to Sovereign Hub (%BRANCH%)...
git push origin %BRANCH% --tags
if %errorlevel% neq 0 (
    echo [ERROR] Push failed. Check remote connectivity or credentials.
    pause
    exit /b %errorlevel%
)

echo.
echo [🎓] MASTER SYNC COMPLETE. GRADUATION DOCUMENTS DISTRIBUTED.
echo.
pause
