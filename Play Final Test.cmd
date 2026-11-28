@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" polish_playtest.py
) else if exist "%USERPROFILE%\KARZ-Tower-Defense\.venv\Scripts\python.exe" (
    "%USERPROFILE%\KARZ-Tower-Defense\.venv\Scripts\python.exe" polish_playtest.py
) else (
    python polish_playtest.py
)
if errorlevel 1 pause
