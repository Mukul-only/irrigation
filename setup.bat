@echo off
echo ================================================
echo   AI Irrigation System - First Time Setup
echo ================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://python.org/downloads
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment...
python -m venv venv

echo [2/3] Installing dependencies...
call venv\Scripts\activate
pip install -r requirements.txt --quiet

echo [3/3] Seeding default plant profiles...
python seed.py

echo.
echo ================================================
echo   Setup complete! Run start.bat to launch.
echo ================================================
pause
