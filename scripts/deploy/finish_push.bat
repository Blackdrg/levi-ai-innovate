@echo off
echo LEVI-AI v4.5 OMNIPRESENT - Global Launch Sync
echo ------------------------------------------------

echo [1/4] Building Frontend Optimized Assets (CSS)...
cd frontend
call npm install
if %ERRORLEVEL% NEQ 0 (
    cd ..
    goto :error
)
call npm run build
if %ERRORLEVEL% NEQ 0 (
    cd ..
    goto :error
)
cd ..

echo [2/4] Staging all architectural updates...
git add .
if %ERRORLEVEL% NEQ 0 goto :error

echo [3/4] Committing the architectural sign-off (Phase 2 Fixes)...
git commit -m "fix: critical pre-launch fixes - chat router, firebase config, json-logger, auth-race"
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] git commit was skipped or failed.
)

echo [4/4] Synchronizing with GitHub (Branch: main)...
git push origin main
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] main push failed.
)

if %ERRORLEVEL% NEQ 0 goto :error

echo Global Launch Initiated!
echo Check your Actions tab at: https://github.com/Blackdrg/LEVI-AI/actions
pause
exit /b 0

:error
echo [ERROR] A critical step failed. Please check the logs above.
pause
exit /b 1
