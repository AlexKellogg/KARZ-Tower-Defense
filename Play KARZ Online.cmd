@echo off
title KARZ Tower Defense
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run: setting up Python. This takes a minute or two...
  py -3.12 -m venv .venv 2>nul || py -3 -m venv .venv 2>nul || python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
  echo Python was not found. Install Python 3.12 from python.org, then run this again.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, httpx, pygame, pytmx, sqlalchemy" 2>nul
if errorlevel 1 (
  echo Installing game and server packages...
  ".venv\Scripts\python.exe" -m pip install -q -r server\requirements.txt
)
".venv\Scripts\python.exe" -c "import sqlalchemy" 2>nul
if errorlevel 1 (
  echo Windows Smart App Control blocked SQLAlchemy's compiled files. Switching to the plain-Python version...
  ".venv\Scripts\python.exe" -m pip install -q --force-reinstall --no-deps "https://files.pythonhosted.org/packages/c1/69/c75534e336b06b3fd3f76de73d89736510800e60c77c58d4e4ce18389018/sqlalchemy-2.1.6-py3-none-any.whl"
)
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, httpx, pygame, pytmx, sqlalchemy, server.app" 2>nul
if errorlevel 1 (
  echo Setup failed. Details:
  ".venv\Scripts\python.exe" -c "import server.app"
  pause
  exit /b 1
)
start "KARZ server - close this window to stop the server" cmd /k .venv\Scripts\python.exe -m uvicorn server.app:create_app --factory --port 8000
echo Starting the KARZ server...
timeout /t 4 /nobreak >nul
".venv\Scripts\python.exe" main.py --server http://127.0.0.1:8000
if errorlevel 1 pause
