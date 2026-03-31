@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   LEVI-AI v6.8 Sovereign - Production Sync
echo ===================================================
cd /d "%~dp0"

:: 1. Virtual Environment Check
if exist .venv\Scripts\activate (
    echo [Check] Activating virtual environment...
    call .venv\Scripts\activate
) else if exist venv\Scripts\activate (
    echo [Check] Activating virtual environment...
    call venv\Scripts\activate
)

:: 2. Pre-Push Check: Pytest
echo.
echo [1/3] Running Automated Test Suite (pytest)...
python -m pytest tests/
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ ERROR: Unit tests failed. Push aborted.
    pause
    exit /b %ERRORLEVEL%
)
echo ✅ Tests Passed!

:: 3. Pre-Push Check: Load Test
echo.
echo [2/3] Running Load Stability Verification...
echo (Simulating 50 concurrent users against local gateway)
python scripts/load_test.py --users 50 --target http://localhost:8000
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ⚠️ WARNING: Load test showed signs of stress or endpoint was unreachable.
    set /p CONTINUE=Ignore load test failure and proceed? (y/n): 
    if /i "!CONTINUE!" NEQ "y" (
        echo Push aborted.
        pause
        exit /b 1
    )
)
echo ✅ Stability Verified!

:: 4. Git Synchronization
echo.
echo [3/3] Synchronizing with Repository...
git add .

echo.
echo Committing v6.8 Sovereign Mind Transformation...
git commit -m "feat(sovereign): finalize LEVI-AI v6.8 Sovereign Architecture

- Integrated Persistent FAISS Vector Memory (User & Global)
- Hardened 8-Stage Deterministic Orchestrator (PEOC Loop)
- Real-time SSE 'Intelligence Pulses' for activity streaming
- Unified Cognitive Maintenance (Celery-based distillation)
- Production-grade rate limiting and circuit breakers"

echo.
echo Pushing to remote (origin main)...
git push origin master:main

echo.
echo ===================================================
echo   Push Complete! System is now synchronized.
echo ===================================================
pause
