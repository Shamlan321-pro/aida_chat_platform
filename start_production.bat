@echo off
echo Starting AIDA Platform in Production Mode...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Set production environment variables
set FLASK_DEBUG=False
set FLASK_ENV=production

echo Environment variables set:
echo FLASK_DEBUG=False
echo FLASK_ENV=production
echo.

REM Check if required environment variables are set
if "%FLASK_SECRET_KEY%"=="" (
    echo Warning: FLASK_SECRET_KEY not set. Please set it before running in production.
    echo You can set it by running: set FLASK_SECRET_KEY=your-secret-key
    echo.
)

if "%GOOGLE_API_KEY%"=="" (
    echo Warning: GOOGLE_API_KEY not set. Please set it before running in production.
    echo You can set it by running: set GOOGLE_API_KEY=your-google-api-key
    echo.
)

echo Starting server...
python start_production.py

pause 