@echo off
REM start.bat — Sovereign OS v13.1.0 "Absolute Monolith" Graduation Launcher
setlocal

echo [🚀] Initializing LEVI-AI v13.1.0 Graduation Tier...

REM 1. Infrastructure Checks
echo [🏗️] Starting Core Infrastructure (Postgres, Redis, Neo4j, Ollama)...
docker compose up -d postgres redis neo4j ollama
if %errorlevel% neq 0 (
    echo [ERROR] Docker infrastructure failed to start.
    pause
    exit /b %errorlevel%
)

REM 2. Environment Validation
if not exist .env (
    echo [⚠️] .env missing. Creating from graduation defaults...
    copy .env.example .env
)

REM 3. Service Readiness
echo [⏳] Waiting for Postgres SQL Fabric...
:WAITPOSTGRES
docker compose exec postgres pg_isready -U levi >nul 2>&1
if errorlevel 1 (
    timeout /t 2 /nobreak >nul
    goto WAITPOSTGRES
)
echo [OK] SQL Fabric Ready.

REM 4. Graduation Initialization
echo [🧬] Running Genesis Seed (Standard Agents & Admin)...
docker compose exec api python backend/scripts/seed_sovereign.py
if %errorlevel% neq 0 (
    echo [⚠️] Genesis seed already initialized or failed. Continuing...
)

echo [📦] Generating Software Bill of Materials (SBOM)...
docker compose exec api python backend/scripts/generate_sbom.py

REM 5. Neural Verification
echo [🛡️] Executing Graduation Audit (28-Point Suite)...
docker compose exec api pytest tests/v13_hardening_test.py
if %errorlevel% neq 0 (
    echo [WARNING] Some graduation tests failed. Check logs for compliance gaps.
)

REM 6. App Launch
echo [🏗️] Finalizing Neural Frontend & Worker Swarm...
docker compose up -d api worker nginx prometheus grafana

echo.
echo [🎓] LEVI-AI v13.1.0 IS LIVE.
echo    ------------------------------------------
echo    Frontend:   http://localhost (Sovereign)
echo    API Docs:   http://localhost/docs
echo    Monitoring: http://localhost:3000 (Grafana)
echo    ------------------------------------------
echo    Mission Control: Absolute Monolith Status [ACTIVE]
echo.
pause
