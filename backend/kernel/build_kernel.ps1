# build_kernel.ps1
# Helper script to build the Levi Rust Kernel bindings for Python

Write-Host "[Kernel-Builder] Commencing Rust Kernel Build..." -ForegroundColor Cyan

# 1. Check for Cargo
if (!(Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Error "Cargo not found! Please install Rust from https://rustup.rs"
    exit 1
}

# 2. Check for maturin
try {
    & python -m maturin --version | Out-Null
} catch {
    Write-Host "Installing maturin build tool..." -ForegroundColor Yellow
    & python -m pip install maturin
}

# 3. Build and Install
Write-Host "Building Python bindings (this may take a few minutes)..." -ForegroundColor Green

$scriptPath = Split-Path $MyInvocation.MyCommand.Path
Push-Location $scriptPath

maturin develop --release

$buildStatus = $LASTEXITCODE
Pop-Location

if ($buildStatus -eq 0) {
    Write-Host "[Kernel-Builder] Rust Kernel build successful and installed." -ForegroundColor Cyan
} else {
    Write-Error "Build failed. Please ensure you have the necessary MSVC Build Tools installed."
}
