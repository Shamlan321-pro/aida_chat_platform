#!/usr/bin/env python3
"""
Production configuration for AIDA Platform
Use this configuration for production deployment
"""

import os
import logging

# Production environment variables
os.environ.setdefault("FLASK_DEBUG", "False")
os.environ.setdefault("FLASK_ENV", "production")

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('aida_production.log'),
        logging.StreamHandler()
    ]
)

# Production settings
PRODUCTION_SETTINGS = {
    'DEBUG': False,
    'TESTING': False,
    'PROPAGATE_EXCEPTIONS': True
}

# Required environment variables for production
REQUIRED_ENV_VARS = [
    'FLASK_SECRET_KEY',
    'GOOGLE_API_KEY'
]

def validate_production_config():
    """Validate that all required environment variables are set"""
    missing_vars = []
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Validate secret key strength
    secret_key = os.getenv('FLASK_SECRET_KEY')
    if len(secret_key) < 32:
        print("WARNING: FLASK_SECRET_KEY should be at least 32 characters for production")
    
    print("✅ Production configuration validated successfully")

if __name__ == "__main__":
    try:
        validate_production_config()
        print("Production configuration is ready!")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        exit(1) 