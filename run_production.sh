#!/bin/bash
# Production server startup script for Aida Mocxha AI Agent API
# This script runs the server without debug mode and auto-restart

echo "Starting Aida Mocxha AI Agent API in Production Mode..."
echo

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: Virtual environment not found. Using system Python."
fi

# Set production environment variables (modify as needed)
export FLASK_ENV=production
export FLASK_SECRET_KEY="your-very-long-secret-key-here-at-least-32-characters-change-this"
export GOOGLE_API_KEY="your-google-api-key-here"

# Check if Gunicorn is available
if python -c "import gunicorn" 2>/dev/null; then
    echo "Using Gunicorn for production server..."
    gunicorn -c gunicorn.conf.py production_server:application
elif python -c "import waitress" 2>/dev/null; then
    echo "Using Waitress for production server..."
    waitress-serve --host=0.0.0.0 --port=5000 --threads=4 production_server:application
else
    echo "Neither Gunicorn nor Waitress found. Using production Flask server..."
    echo "Warning: For better performance, install Gunicorn or Waitress:"
    echo "  pip install gunicorn"
    echo "  pip install waitress"
    echo
    python production_server.py
fi

echo
echo "Server stopped."