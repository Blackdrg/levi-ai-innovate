# scripts/initialize_swarm.ps1
# Sovereign OS Swarm Initialization Script

Write-Host "🪐 [LEVI Swarm] Checking Docker status..." -ForegroundColor Cyan

# 1. Verify Docker is running
docker version >$null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Docker is not running. Please start Docker Desktop."
    exit 1
}

# 2. Check Swarm Status
$swarmStatus = docker info --format '{{.Swarm.LocalNodeState}}'
if ($swarmStatus -eq "active") {
    Write-Host "✅ Swarm is already active." -ForegroundColor Green
} else {
    Write-Host "🏗️  Initializing Docker Swarm..." -ForegroundColor Yellow
    docker swarm init --advertise-addr 127.0.0.1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Failed to initialize Swarm."
        exit 1
    }
    Write-Host "✅ Swarm initialized successfully." -ForegroundColor Green
}

# 3. Create Networks
Write-Host "🌐 Creating Sovereign Overlay Networks..." -ForegroundColor Cyan
docker network create --driver overlay --attachable levi-backplane
docker network create --driver overlay --attachable levi-mesh

# 4. Deploy Stack
Write-Host "🚀 Deploying LEVI Sovereign Stack..." -ForegroundColor Cyan
docker stack deploy -c docker-compose.yml levi-sovereign

Write-Host "✨ [LEVI Swarm] Swarm setup complete. Monitor results at http://localhost:8080" -ForegroundColor Green
