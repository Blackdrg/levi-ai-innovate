@echo off
setlocal
echo --------------------------------------------------
echo    🧠 LEVI-AI .venv Creator        
echo    Setting up the virtual environment...
echo --------------------------------------------------

:: 1. Create the virtual environment if it doesn't exist
if not exist ".venv" (
    echo 🚀 Creating virtual environment...
    python -m venv .venv
) else (
    echo ✅ .venv directory already exists.
)

:: 2. Upgrade pip
echo 🆙 Upgrading pip...
.\.venv\Scripts\python.exe -m pip install --upgrade pip

:: 3. Install requirements (First attempt)
if exist "backend\requirements.txt" (
    echo 📦 Installing backend dependencies...
    :: We try to install everything first. If llama-cpp-python fails, we'll fix it in the next step.
    .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    
    :: 4. Specifically fix llama-cpp-python if it failed (common on Windows without VS Build Tools)
    echo 🛠️ Checking llama-cpp-python...
    .\.venv\Scripts\python.exe -c "import llama_cpp" 2>nul
    if errorlevel 1 (
        echo ⚠️ llama-cpp-python installation failed or is missing.
        echo 🔄 Attempting to install pre-compiled CPU wheel (no compiler required)...
        .\.venv\Scripts\python.exe -m pip install llama-cpp-python==0.2.76 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
    ) else (
        echo ✅ llama-cpp-python is correctly installed.
    )
) else (
    echo ❌ ERROR: backend\requirements.txt not found.
)

echo --------------------------------------------------
echo ✅ MISSION_COMPLETE: Virtual environment ".venv" is ready.
echo 🔗 To activate: .\.venv\Scripts\activate
echo --------------------------------------------------
pause
