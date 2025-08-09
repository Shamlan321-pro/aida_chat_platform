#!/usr/bin/env python3
"""
Production startup script for AIDA Platform
Use this script to start the server in production mode
"""

import os
import sys
import logging
from aida_api_server import app

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('aida_production.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def start_production_server():
    """Start the Flask app in production mode"""
    
    # Set production environment variables
    os.environ.setdefault("FLASK_DEBUG", "False")
    os.environ.setdefault("FLASK_ENV", "production")
    
    # Validate required environment variables
    required_vars = ['FLASK_SECRET_KEY', 'GOOGLE_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set the following environment variables:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        sys.exit(1)
    
    # Validate secret key strength
    secret_key = os.getenv('FLASK_SECRET_KEY')
    if len(secret_key) < 32:
        logger.warning("FLASK_SECRET_KEY should be at least 32 characters for production")
    
    logger.info("Starting Aida ERPNext AI Agent API server in PRODUCTION mode...")
    logger.info("Server will be available at: http://0.0.0.0:5000")
    
    try:
        # Start the Flask app in production mode
        app.run(
            debug=False,
            host='0.0.0.0',
            port=5000,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_production_server() 