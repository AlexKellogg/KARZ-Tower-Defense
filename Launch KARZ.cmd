@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment is missing. Follow README.md to set it up.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "preview.py"
if errorlevel 1 pause
