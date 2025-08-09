import os
from typing import Optional

class Config:
    """Configuration class for AIDA Platform."""
    
    # MongoDB Configuration
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "aida_platform")
    MONGODB_CONVERSATIONS_DB = os.getenv("MONGODB_CONVERSATIONS_DB", "aida_ai_conversations")
    
    # ERPNext Configuration
    ERPNEXT_URL = os.getenv("ERPNEXT_URL", "http://localhost:8000")
    ERPNEXT_USERNAME = os.getenv("ERPNEXT_USERNAME", "Administrator")
    ERPNEXT_PASSWORD = os.getenv("ERPNEXT_PASSWORD", "admin")
    
    # Google API Configuration
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
    
    # Flask Configuration
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "supersecretkey_aida_erpnext_agent")
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    # Session Configuration
    SESSION_EXPIRY_DAYS = int(os.getenv("SESSION_EXPIRY_DAYS", "30"))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate_mongodb_connection(cls) -> bool:
        """Validate MongoDB connection."""
        try:
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
            
            client = MongoClient(cls.MONGODB_URI, serverSelectionTimeoutMS=5000)
            client.admin.command('ismaster')
            client.close()
            return True
        except Exception as e:
            print(f"❌ MongoDB connection validation failed: {e}")
            return False
    
    @classmethod
    def get_mongodb_uri(cls) -> str:
        """Get MongoDB URI with validation."""
        if not cls.validate_mongodb_connection():
            raise Exception("MongoDB connection failed. Please check your MongoDB installation and connection string.")
        return cls.MONGODB_URI
    
    @classmethod
    def print_config(cls):
        """Print current configuration."""
        print("🔧 AIDA Platform Configuration:")
        print(f"  MongoDB URI: {cls.MONGODB_URI}")
        print(f"  MongoDB DB Name: {cls.MONGODB_DB_NAME}")
        print(f"  ERPNext URL: {cls.ERPNEXT_URL}")
        print(f"  Flask Host: {cls.FLASK_HOST}")
        print(f"  Flask Port: {cls.FLASK_PORT}")
        print(f"  Session Expiry: {cls.SESSION_EXPIRY_DAYS} days")
        print(f"  Log Level: {cls.LOG_LEVEL}")
