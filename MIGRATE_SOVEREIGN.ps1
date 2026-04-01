# MIGRATE_SOVEREIGN.ps1
# LEVI-AI v6.8.8 Sovereign REFACTORING AUTOMATION

Write-Host "--- Initiating Sovereign Refactor Protocol ---" -ForegroundColor Cyan

# 1. Backup critical environments
Write-Host "[1/5] Shielding Environment Configurations..." -ForegroundColor Yellow
if (Test-Path ".env") { Copy-Item ".env" "configs/.env.bak" -Force }

# 2. Reorganize Root structure
Write-Host "[2/5] Synthesizing Top-Level Layers..." -ForegroundColor Yellow
$folders = @("frontend", "backend", "shared", "configs", "docs")
foreach ($f in $folders) { if (!(Test-Path $f)) { New-Item -ItemType Directory -Path $f } }

# 3. Clean legacy Frontend
Write-Host "[3/5] Decommissioning Legacy Frontend UI..." -ForegroundColor Yellow
if (Test-Path "frontend_react") {
    Move-Item "frontend_react/*" "frontend/" -Force -ErrorAction SilentlyContinue
    Remove-Item "frontend_react" -Recurse -Force
}

# 4. Restructure Backend (Layering)
Write-Host "[4/5] Aligning Backend Intelligence OS..." -ForegroundColor Yellow
$layers = @("api", "core", "engines", "models", "services", "utils", "config")
foreach ($l in $layers) { if (!(Test-Path "backend/$l")) { New-Item -ItemType Directory -Path "backend/$l" } }

# Specifically move key OS modules
Move-Item "backend/main.py" "backend/api/" -Force
Move-Item "backend/generation.py" "backend/engines/chat/" -Force
Move-Item "backend/services/orchestrator/*" "backend/core/" -Force -ErrorAction SilentlyContinue
Move-Item "backend/payments.py" "backend/services/" -Force
Move-Item "backend/image_gen.py" "backend/services/" -Force
Move-Item "backend/video_gen.py" "backend/services/" -Force

# 5. Finalize Documentation
Write-Host "[5/5] Finalizing Master Documentation..." -ForegroundColor Green
Move-Item "*.md" "docs/" -Force -ErrorAction SilentlyContinue
Move-Item "docker-compose.yml" "configs/" -Force
Move-Item "nginx.conf" "configs/" -Force

Write-Host "--- Sovereign Refactor Phase A: COMPLETE ---" -ForegroundColor Green
Write-Host "Please restart your IDE to re-index the new structure." -ForegroundColor Cyan
