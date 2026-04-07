# Sovereign OS: Data Migration Script (Drive C -> Drive D)
# 🪐 Engineered for Absolute Local Autonomy

$DRIVE_D_ROOT = "D:\LEVI-AI\data"
$USER_PROFILE = $env:USERPROFILE

# Target Directories
$HF_CACHE_SRC = "$USER_PROFILE\.cache\huggingface"
$HF_CACHE_DEST = "$DRIVE_D_ROOT\huggingface"

$PIP_CACHE_SRC = "$USER_PROFILE\AppData\Local\pip\cache"
$PIP_CACHE_DEST = "$DRIVE_D_ROOT\pip_cache"

$NPM_CACHE_SRC = "$USER_PROFILE\.npm"
$NPM_CACHE_DEST = "$DRIVE_D_ROOT\npm_cache"

$OLLAMA_SRC = "$USER_PROFILE\.ollama"
$OLLAMA_DEST = "$DRIVE_D_ROOT\ollama"

# 1. Ensure Target Root Exists
if (!(Test-Path $DRIVE_D_ROOT)) {
    New-Item -ItemType Directory -Path $DRIVE_D_ROOT -Force
}

# 2. Migration Function
function Move-SovereignDirectory {
    param (
        [string]$Source,
        [string]$Destination
    )

    if (Test-Path $Source) {
        Write-Host "📦 Moving $Source to $Destination..."
        
        # Ensure Destination Parent Exists
        $Parent = Split-Path $Destination -Parent
        if (!(Test-Path $Parent)) {
            New-Item -ItemType Directory -Path $Parent -Force
        }

        # Merge Move (Robocopy is safer for large directories)
        robocopy $Source $Destination /E /MOVE /NP /MT:16 /R:3 /W:5
        
        Write-Host "✅ Move completed."
    } else {
        Write-Host "ℹ️  Source $Source not found. Skipping."
    }
}

# 🛠️ Execute Migration
Stop-Process -Name "Ollama" -ErrorAction SilentlyContinue
Move-SovereignDirectory $HF_CACHE_SRC $HF_CACHE_DEST
Move-SovereignDirectory $PIP_CACHE_SRC $PIP_CACHE_DEST
Move-SovereignDirectory $NPM_CACHE_SRC $NPM_CACHE_DEST
Move-SovereignDirectory $OLLAMA_SRC $OLLAMA_DEST

Write-Host "🛡️  Sovereign Residence Hardened. All data now on Drive D."
Write-Host "🚀  You can now run 'bash scripts/launch_production.sh'."
