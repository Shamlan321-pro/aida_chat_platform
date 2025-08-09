#!/usr/bin/env python3
"""
Production server configuration for Aida Mocxha AI Agent API

This file provides a production-ready configuration without debug mode
and auto-restart functionality. Use with WSGI servers like Gunicorn.
"""

import os
import logging
from aida_api_server import app, flask_logger

# Production configuration
def configure_production():
    """Configure the Flask app for production use"""
    
    # Disable debug mode
    app.config['DEBUG'] = False
    
    # Set production logging level
    logging.basicConfig(
        level=logging.WARNING,  # Reduce log verbosity in production
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('aida_production.log'),
            logging.StreamHandler()
        ]
    )
    
    # Ensure required environment variables are set
    required_env_vars = [
        'FLASK_SECRET_KEY',
        'GOOGLE_API_KEY'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        flask_logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Validate secret key strength
    secret_key = os.getenv('FLASK_SECRET_KEY')
    if len(secret_key) < 32:
        flask_logger.warning("FLASK_SECRET_KEY should be at least 32 characters for production")
    
    flask_logger.info("Production configuration applied successfully")

# Configure for production when this module is imported
configure_production()

# WSGI application object for production servers
application = app

if __name__ == '__main__':
    # This should not be used in production
    # Use a WSGI server like Gunicorn instead
    flask_logger.warning("Running in development mode. Use a WSGI server for production!")
    app.run(host='0.0.0.0', port=5000, debug=False)