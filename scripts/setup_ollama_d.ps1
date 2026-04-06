# setup_ollama_d.ps1
# This script sets up the environment variables for Ollama on Drive D and runs the installer.

$InstallPath = "D:\Ollama"
$ModelsPath = "D:\Ollama\models"

# 1. Create directories if they don't exist
if (-not (Test-Path $InstallPath)) {
    New-Item -ItemType Directory -Path $InstallPath -Force
}
if (-not (Test-Path $ModelsPath)) {
    New-Item -ItemType Directory -Path $ModelsPath -Force
}

# 2. Set persistent User environment variables
Write-Host "Setting persistent environment variables..."
[System.Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $ModelsPath, "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_INSTALL_DIR", $InstallPath, "User")

# 3. Set current session environment variables
$env:OLLAMA_INSTALL_DIR = $InstallPath
$env:OLLAMA_MODELS = $ModelsPath

# 4. Run the main installation script
Write-Host "Starting Ollama installation to $InstallPath..."
Write-Host "Models will be stored in $ModelsPath"

# Assuming the script is in d:\LEVI-AI\scripts\setup_ollama_d.ps1, the installer is in d:\LEVI-AI\install_ollama.ps1
$InstallerScript = Join-Path $PSScriptRoot "..\install_ollama.ps1"

if (Test-Path $InstallerScript) {
    & $InstallerScript
} else {
    Write-Error "Could not find install_ollama.ps1 at $InstallerScript"
}

Write-Host "Setup complete. Please restart your terminal or the Ollama application to ensure all changes take effect."
