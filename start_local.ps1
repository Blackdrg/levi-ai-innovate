# Run this script to start the backend and frontend locally without Docker
# Requirement: Python installed

# 1. Setup virtual environment
if (!(Test-Path venv)) {
    python -m venv venv
}
.\venv\Scripts\activate
pip install -r backend/requirements.txt

# 2. Seed database
python -m backend.seed

# 3. Start backend in a new window
Start-Process powershell -ArgumentList ".\venv\Scripts\activate; uvicorn backend.main:app --host 127.0.0.1 --port 8000"

# 4. Start Rasa services
pip install -r rasa/requirements.txt
Start-Process powershell -ArgumentList ".\\venv\\Scripts\\activate; rasa train"
Start-Process powershell -ArgumentList ".\\venv\\Scripts\\activate; rasa run --enable-api --cors \`"*\`" -m models --port 5005 --debug"
Start-Process powershell -ArgumentList ".\\venv\\Scripts\\activate; rasa run actions"

# 5. Start frontend in a new window
Start-Process powershell -ArgumentList "python -m http.server 8080 --directory frontend"

Write-Host "LEVI is running!"
Write-Host "Frontend: http://localhost:8080"
Write-Host "Backend: http://localhost:8000"
Write-Host "Rasa Server: http://localhost:5005"
Write-Host "Rasa Actions: http://localhost:5055"
