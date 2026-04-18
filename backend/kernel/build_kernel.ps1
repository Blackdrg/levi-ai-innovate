# build_kernel.ps1
# Helper script to build the Levi Rust Kernel bindings for Python

Write-Host "[Kernel-Builder] Commencing Rust Kernel Build..." -ForegroundColor Cyan

# 1. Check for Cargo and Toolchain
if (!(Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Error "Cargo not found! Please install Rust from https://rustup.rs"
    exit 1
}

# Ensure a default toolchain is configured (Fix for 'rustup could not choose a version' error)
try {
    & rustc --version >$null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[Kernel-Builder] No default Rust toolchain detected. Setting to stable..." -ForegroundColor Yellow
        & rustup default stable
    }
} catch {
    Write-Host "[Kernel-Builder] Configuring stable toolchain..." -ForegroundColor Yellow
    & rustup default stable
}

# 2. Check for maturin
python -m maturin --version >$null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing maturin build tool..." -ForegroundColor Yellow
    python -m pip install maturin
}

# 3. Build and Install
Write-Host "Building Python bindings (this may take a few minutes)..." -ForegroundColor Green

$scriptPath = Split-Path $MyInvocation.MyCommand.Path
Push-Location $scriptPath

python -m maturin develop --release

$buildStatus = $LASTEXITCODE
Pop-Location

# 4. Build Bare-Metal Kernel (HAL-0 Native)
Write-Host "`n[Kernel-Builder] Commencing Bare-Metal (no_std) Kernel Build..." -ForegroundColor Cyan
Push-Location "$scriptPath\bare_metal"

# Ensure target is installed
& rustup target add x86_64-unknown-none

Write-Host "Compiling HAL-0 Native binary for x86_64-unknown-none..." -ForegroundColor Green
& cargo build --release --target x86_64-unknown-none

if ($LASTEXITCODE -eq 0) {
    Write-Host "[Kernel-Builder] Bare-Metal Kernel binary built successfully: .\target\x86_64-unknown-none\release\hal0-bare" -ForegroundColor Cyan
} else {
    Write-Host "[ERROR] Bare-Metal build failed. Ensure 'no_std' dependencies are compatible." -ForegroundColor Red
}
Pop-Location

if ($buildStatus -eq 0) {
    Write-Host "`n[Kernel-Builder] ALL SOVEREIGN LAYERS GRADUATED." -ForegroundColor Cyan
} else {
    Write-Error "Build cycle completed with errors. See above."
}
