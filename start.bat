@echo off
REM start.bat — full system bootstrap for Windows (Native)

echo ==> Synthesizing Neural Frontend (Phase 2)...
cd levi-frontend
if exist node_modules (
    echo [OK] Dependencies loaded.
) else (
    echo [📦] Installing dependencies...
    call npm install
)
echo [🏗️] Building v13 artifacts...
call npm run build
cd ..

echo ==> Starting infrastructure (Postgres, Redis, Neo4j)...
docker compose up -d postgres redis neo4j

echo ==> Waiting for Postgres to be ready...
:WAITPOSTGRES
docker compose exec postgres pg_isready -U levi >nul 2>&1
if errorlevel 1 (
    echo Postgres is unavailable - sleeping
    timeout /t 2 /nobreak >nul
    goto WAITPOSTGRES
)

echo ==> Running v13 migrations...
docker compose exec postgres psql -U levi -d levi_db -f /docker-entrypoint-initdb.d/init.sql

echo ==> Starting Ollama
docker compose up -d ollama
echo ==> Waiting for Ollama models...
docker compose run --rm ollama-init

echo ==> Starting API, Workers, and Nginx...
docker compose up -d api worker nginx

echo ==> Starting observability (Prometheus/Grafana)...
docker compose up -d prometheus grafana

echo.
echo [OK] LEVI-AI is live (v13.0.0 Monolith).
echo    API:      https://localhost/api/
echo    Grafana:  http://localhost:3000
echo    Neo4j UI: http://localhost:7474
echo    Ollama:   http://localhost:11434
pause
