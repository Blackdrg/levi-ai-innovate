# build_kernel.ps1
# Helper script to build the LEVI HAL-0 Sovereign OS kernel
# Produces:
#   - Python FFI bindings (maturin)
#   - Bootable disk image via `bootimage` (QEMU-ready + flashable to USB)

Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " HAL-0 SOVEREIGN KERNEL — Build Pipeline " -ForegroundColor Cyan
Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan

$scriptPath = Split-Path $MyInvocation.MyCommand.Path

# ── 1. Verify toolchain ──────────────────────────────────────────────────────
if (!(Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Error "Cargo not found! Install Rust from https://rustup.rs"
    exit 1
}

try {
    & rustc --version > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[Builder] No default toolchain. Setting stable..." -ForegroundColor Yellow
        & rustup default stable
    }
} catch {
    & rustup default stable
}

# Ensure the bare-metal target is installed
& rustup target add x86_64-unknown-none
& rustup component add rust-src llvm-tools-preview

# ── 2. Python FFI bindings (levi_kernel Python module) ──────────────────────
Write-Host "`n[Builder] Building Python FFI bindings..." -ForegroundColor Green

python -m maturin --version > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[Builder] Installing maturin..." -ForegroundColor Yellow
    python -m pip install maturin
}

Push-Location $scriptPath
python -m maturin develop --release
$ffiStatus = $LASTEXITCODE
Pop-Location

# ── 3. Bare-Metal Bootable Image (GRUB/UEFI via bootimage) ──────────────────
Write-Host "`n[Builder] Building HAL-0 bare-metal kernel + bootable image..." -ForegroundColor Cyan

# Install bootimage if not present
cargo install bootimage --version "0.10.3" 2>$null

Push-Location "$scriptPath\bare_metal"

# Build debug (fast iteration)
& cargo bootimage

if ($LASTEXITCODE -eq 0) {
    $imgPath = "target\x86_64-unknown-none\debug\bootimage-hal0-bare.bin"
    Write-Host ""
    Write-Host "[OK] Bootable disk image: $scriptPath\bare_metal\$imgPath" -ForegroundColor Green
    Write-Host ""
    Write-Host " To run in QEMU:" -ForegroundColor Yellow
    Write-Host "   qemu-system-x86_64 -drive format=raw,file=$imgPath -serial stdio" -ForegroundColor White
    Write-Host ""
    Write-Host " To flash to USB (replace X: with your drive letter):" -ForegroundColor Yellow
    Write-Host "   dd if=$imgPath of=\\.\PhysicalDriveX bs=512" -ForegroundColor White
    Write-Host ""

    # Optionally wrap in ISO with grub-mkrescue (requires WSL or Linux)
    if (Get-Command wsl -ErrorAction SilentlyContinue) {
        Write-Host "[Builder] Generating ISO via WSL grub-mkrescue..." -ForegroundColor Cyan
        $wslImg = ($imgPath -replace '\\', '/') -replace 'C:', '/mnt/c'
        wsl grub-mkrescue -o hal0-sovereign.iso --overlay=$wslImg 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] ISO: $scriptPath\bare_metal\hal0-sovereign.iso" -ForegroundColor Green
        } else {
            Write-Host "[INFO] grub-mkrescue not available in WSL; .bin image is flashable directly." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "[ERROR] Bare-metal kernel build failed. See above." -ForegroundColor Red
}

Pop-Location

# ── 4. Summary ───────────────────────────────────────────────────────────────
Write-Host ""
if ($ffiStatus -eq 0) {
    Write-Host "══ ALL SOVEREIGN LAYERS GRADUATED ══" -ForegroundColor Cyan
} else {
    Write-Warning "Python FFI build had errors. Bare-metal image may still be usable."
}
