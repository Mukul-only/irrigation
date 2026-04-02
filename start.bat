@echo off
echo ================================================
echo   AI Irrigation System - Starting Server
echo ================================================
echo.

:: Activate virtual environment
call venv\Scripts\activate

echo Server starting on http://localhost:8000
echo Swagger UI: http://localhost:8000/docs
echo Press CTRL+C to stop.
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
