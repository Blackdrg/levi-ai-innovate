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

if ($buildStatus -eq 0) {
    Write-Host "[Kernel-Builder] Rust Kernel build successful and installed." -ForegroundColor Cyan
} else {
    Write-Host "`n[ERROR] Build failed." -ForegroundColor Red
    if ($buildStatus -ne 0 -and $null -eq (Get-Command link.exe -ErrorAction SilentlyContinue)) {
        Write-Host "CRITICAL: MSVC Linker (link.exe) not found in PATH." -ForegroundColor Yellow
        Write-Host "Please ensure you have installed 'Desktop development with C++' in your Visual Studio Installer." -ForegroundColor Gray
        Write-Host "URL: https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor White
        Write-Host "`nPRO-TIP: Run this script from the 'Developer PowerShell for VS 2022' if installations exist." -ForegroundColor Cyan
    } else {
        Write-Error "Build failed during cargo execution. Check the logs above for specific Rust/C++ errors."
    }
}
