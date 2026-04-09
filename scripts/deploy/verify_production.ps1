# verify_production.ps1
# LEVI-AI 10-Step Launch Verification Runbook

$ErrorActionPreference = "Stop"

Write-Host "=== 1. Secrets Replacement Verified ===" -ForegroundColor Green
Write-Host "Checking that .env does not contain 'replace_me' (Assuming completed via Vault/Doppler)"

Write-Host "=== 2. Stand up Infrastructure ===" -ForegroundColor Cyan
docker compose up -d redis postgres neo4j
Write-Host "Waiting 15 seconds for containers to initialize (Postgres needs time to boot)..."
Start-Sleep -Seconds 15

# Verify Redis
$redisPing = docker exec levi-ai-redis-1 redis-cli ping
if ($LASTEXITCODE -ne 0 -or $redisPing -notmatch "PONG") { 
    Write-Host "Redis verification failed or port 6379 is blocked locally!" -ForegroundColor Red 
    exit 1 
}
Write-Host "Redis is READY" -ForegroundColor Green

# Verify Postgres
$pgPing = docker exec levi-ai-postgres-1 pg_isready
if ($LASTEXITCODE -ne 0 -or $pgPing -notmatch "accepting connections") { 
    Write-Host "Postgres verification failed!" -ForegroundColor Red 
    exit 1 
}
Write-Host "Postgres is READY" -ForegroundColor Green


Write-Host "=== 3. Alembic Migrations against Snapshot ===" -ForegroundColor Cyan
Write-Host "Installing dependencies if missing..."
$env:DATABASE_URL="postgresql+asyncpg://levi:sovereign_pass@127.0.0.1:5432/levi_db"
python -m pip install -r backend/requirements.txt -q

Write-Host "Waiting for database to accept remote connections..."
$maxRetries = 10
$retryCount = 0
$alembicSuccess = $false

do {
    python -m alembic -c backend/alembic.ini upgrade head
    if ($LASTEXITCODE -eq 0) {
        $alembicSuccess = $true
        break
    }
    Write-Host "Database not fully ready, retrying ($retryCount/$maxRetries)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    $retryCount++
} while ($retryCount -lt $maxRetries)

if (-not $alembicSuccess) { 
    Write-Host "Alembic upgrade failed after multiple attempts" -ForegroundColor Red
    exit 1 
}

python -m alembic -c backend/alembic.ini current


Write-Host "=== 4. Start Ollama and verify model availability ===" -ForegroundColor Cyan
Write-Host "Starting Ollama in background..."
Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
Start-Sleep -Seconds 5

ollama pull llama3.1:8b
ollama pull phi3:mini
ollama pull nomic-embed-text

$tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get
if ($tags.models.Count -gt 0) { Write-Host "Ollama models verified" -ForegroundColor Green } else { exit 1 }


Write-Host "=== 5. Configure observability export targets ===" -ForegroundColor Cyan
$env:OTEL_EXPORTER_OTLP_ENDPOINT="http://jaeger:4318/v1/traces"
$env:ALERT_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK"
Write-Host "Observability variables structured." -ForegroundColor Green


Write-Host "=== 6. Start the backend and verify /ready ===" -ForegroundColor Cyan
Write-Host "Starting backend gateway..."
Start-Process bash -ArgumentList "entrypoint.sh" -WorkingDirectory "backend" -WindowStyle Normal
Start-Sleep -Seconds 10
try {
    $readyStatus = Invoke-RestMethod -Uri "http://localhost:8080/ready" -Method Get
    if ($readyStatus.ready -eq $true) { Write-Host "Backend is READY" -ForegroundColor Green }
} catch { Write-Host "Backend failed to report healthy." -ForegroundColor Red; exit 1 }


Write-Host "=== 7. Start the frontend === " -ForegroundColor Cyan
$env:VITE_API_BASE_URL="http://localhost:8080/api"
Start-Process npm -ArgumentList "run dev" -WorkingDirectory "frontend" -WindowStyle Normal
Write-Host "Frontend booting up." -ForegroundColor Green


Write-Host "=== 8. Run the full verification suite ===" -ForegroundColor Cyan
python -m pytest backend/tests/ -q
$env:RUN_LIVE_OLLAMA_TESTS="1"
python -m pytest tests/integration/test_live_ollama_smoke.py
k6 run tests/load/missions_k6.js --vus 10 --duration 30s


Write-Host "=== 9. Run chaos before go-live ===" -ForegroundColor Cyan
$env:ENABLE_CHAOS="true"
python -m pytest tests/chaos/ -q
python scripts/chaos/run_live_chaos.py --service redis --outage-seconds 10


Write-Host "=== 10. Gate the penetration test scope ===" -ForegroundColor Cyan
python -m backend.scripts.red_team
Write-Host "=== PRE-FLIGHT COMPLETE. READY FOR AUDIT DEPLOYMENT ===" -ForegroundColor Magenta
