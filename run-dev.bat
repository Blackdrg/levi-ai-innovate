@echo off
title LEVI-AI Dev Server
echo Starting both frontend and backend development servers...

:: Ensure we are in the root directory
cd /d "%~dp0"

:: Start Backend in a new window
echo Starting LEVI Backend (Port 8000)...
start cmd /k "title LEVI Backend && set PYTHONPATH=%%PYTHONPATH%%;%cd%;%cd%\backend && python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000"

:: Start Frontend in a new window
echo Starting LEVI Frontend (Port 8080)...
start cmd /k "title LEVI Frontend && python -m http.server 8080 --bind 127.0.0.1 --directory frontend"

echo Servers are initializing. Visit http://localhost:8080 for the frontend and http://localhost:8000/docs for API docs.
pause
