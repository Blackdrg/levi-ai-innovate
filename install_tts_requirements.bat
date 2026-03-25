@echo off
:: This script installs Visual Studio Build Tools and TTS
:: Run this file as ADMINISTRATOR

cd /d "%~dp0"

echo [1/3] Downloading Visual Studio Build Tools Installer...
powershell -Command "Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vs_BuildTools.exe' -OutFile 'vs_BuildTools.exe'"

echo [2/3] Installing Visual Studio Build Tools (C++ Desktop Workload)...
echo This may take 5-10 minutes depending on internet speed (approx 4.5 GB required).
vs_BuildTools.exe --quiet --wait --norestart --nocache --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended

echo [3/3] Installing TTS package in .venv...
.\.venv\Scripts\pip.exe install TTS

echo.
echo Process complete!
pause
