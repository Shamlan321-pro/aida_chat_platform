@echo off
REM Production server startup script for Aida Mocxha AI Agent API
REM This script runs the server without debug mode and auto-restart

echo Starting Aida Mocxha AI Agent API in Production Mode...
echo.

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found. Using system Python.
)

REM Set production environment variables (modify as needed)
set FLASK_ENV=production
set FLASK_SECRET_KEY=your-very-long-secret-key-here-at-least-32-characters-change-this
set GOOGLE_API_KEY=your-google-api-key-here

REM Check if Gunicorn is available
python -c "import gunicorn" 2>nul
if %errorlevel% == 0 (
    echo Using Gunicorn for production server...
    gunicorn -c gunicorn.conf.py production_server:application
) else (
    echo Gunicorn not found. Checking for Waitress...
    python -c "import waitress" 2>nul
    if %errorlevel% == 0 (
        echo Using Waitress for production server...
        waitress-serve --host=0.0.0.0 --port=5000 --threads=4 production_server:application
    ) else (
        echo Neither Gunicorn nor Waitress found. Using production Flask server...
        echo Warning: For better performance, install Gunicorn or Waitress:
        echo   pip install gunicorn
        echo   pip install waitress
        echo.
        python production_server.py
    )
)

echo.
echo Server stopped.
pause