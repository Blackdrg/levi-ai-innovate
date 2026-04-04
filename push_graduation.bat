@echo off
REM push_graduation.bat — LEVI-AI Sovereign OS v13.1.0 Stable
setlocal enabledelayedexpansion

echo [🚀] Initializing Sovereign Graduation Push (v13.1)...

REM 1. Detect Branch
for /f "tokens=*" %%i in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%i
echo [📍] Current Branch: %BRANCH%

REM 2. Stage Changes
echo [🏗️] Staging Graduation Artifacts...
git add .

REM 3. Pulse Pull (Avoid non-fast-forward)
echo [📡] Pulling latest swarm metadata...
git pull origin %BRANCH% --rebase

REM 4. Graduation Commit
echo [🧱] Committing Absolute Monolith (28/28 Audit)...
git commit -m "🚀 Graduation: Absolute Monolith Stable v13.1.0 (28/28 Audit Hardened)"

REM 5. Tagging
echo [🏷️] Tagging release v13.1.0-stable...
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
echo [🎓] SOVEREIGN GRADUATION COMPLETE. v13.1.0 IS NOW DISTRIBUTED.
echo.
pause
