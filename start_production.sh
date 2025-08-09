#!/bin/bash

echo "Starting AIDA Platform in Production Mode..."
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed or not in PATH"
    exit 1
fi

# Set production environment variables
export FLASK_DEBUG=False
export FLASK_ENV=production

echo "Environment variables set:"
echo "FLASK_DEBUG=False"
echo "FLASK_ENV=production"
echo

# Check if required environment variables are set
if [ -z "$FLASK_SECRET_KEY" ]; then
    echo "Warning: FLASK_SECRET_KEY not set. Please set it before running in production."
    echo "You can set it by running: export FLASK_SECRET_KEY=your-secret-key"
    echo
fi

if [ -z "$GOOGLE_API_KEY" ]; then
    echo "Warning: GOOGLE_API_KEY not set. Please set it before running in production."
    echo "You can set it by running: export GOOGLE_API_KEY=your-google-api-key"
    echo
fi

echo "Starting server..."
python3 start_production.py 