# LEVI Master Build Pipeline
# Usage: .\package_levi.ps1

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting LEVI-AI Windows Packaging Pipeline..." -ForegroundColor Cyan

# 1. Environment Verification
Write-Host "🔍 Verifying dependencies..."
if (!(Get-Command python -ErrorAction SilentlyContinue)) { throw "Python not found" }
if (!(Get-Command npm -ErrorAction SilentlyContinue)) { throw "NPM not found" }
if (!(Get-Command cargo -ErrorAction SilentlyContinue)) { throw "Rust/Cargo not found" }

# 2. Package Backend (PyInstaller)
Write-Host "📦 Packaging LEVI Backend..." -ForegroundColor Green
cd d:\LEVI-AI\desktop
if (!(Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "Installing PyInstaller..."
    pip install pyinstaller
}

# Run PyInstaller
pyinstaller --clean backend.spec

# 3. Prepare Tauri Sidecars
Write-Host "⚙️ Preparing Tauri Sidecars..."
$binDir = "src-tauri\binaries"
if (!(Test-Path $binDir)) { New-Item -ItemType Directory -Path $binDir }

# Tauri expects sidecars to have a target triple suffix (e.g., levi-core-x86_64-pc-windows-msvc.exe)
$targetTriple = "x86_64-pc-windows-msvc"
Copy-Item "dist\levi-core\levi-core.exe" "$binDir\levi-core-$targetTriple.exe"
# Copy necessary DLLs/assets from dist/levi-core
Copy-Item "dist\levi-core\*" "$binDir\" -Recurse -Force

# 4. Build Tauri Shell
Write-Host "🐚 Building LEVI Desktop Shell..." -ForegroundColor Green
# Initialize npm if needed
if (!(Test-Path "package.json")) {
    npm init -y
    npm install @tauri-apps/api @tauri-apps/plugin-shell
}

# Build the app
# Note: This assumes 'npm run build' is configured to build the React frontend
npm run build
cargo tauri build

Write-Host "✅ LEVI-AI Packaging Complete!" -ForegroundColor Cyan
Write-Host "Installer location: d:\LEVI-AI\desktop\src-tauri\target\release\bundle\msi\"
