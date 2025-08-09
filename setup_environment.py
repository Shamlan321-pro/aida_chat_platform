#!/usr/bin/env python3
"""
Environment Setup Script for AIDA Platform
This script helps you configure environment variables for the AIDA platform.
"""

import os
import sys

def setup_environment():
    """Set up environment variables for AIDA Platform."""
    print("🔧 AIDA Platform - Environment Setup")
    print("=" * 40)
    
    # Set default environment variables
    env_vars = {
        "MONGODB_URI": "mongodb://localhost:27017/",
        "MONGODB_DB_NAME": "aida_platform",
        "MONGODB_CONVERSATIONS_DB": "aida_ai_conversations",
        "ERPNEXT_URL": "http://46.62.138.17:8000",
        "ERPNEXT_USERNAME": "Administrator",
        "ERPNEXT_PASSWORD": "admin",
        "FLASK_SECRET_KEY": "supersecretkey_aida_erpnext_agent",
        "FLASK_HOST": "0.0.0.0",
        "FLASK_PORT": "5000",
        "FLASK_DEBUG": "False",
        "SESSION_EXPIRY_DAYS": "30",
        "LOG_LEVEL": "INFO"
    }
    
    print("📝 Current configuration:")
    for key, value in env_vars.items():
        print(f"  {key}: {value}")
    
    print("\n🔑 API Keys Configuration:")
    print("You need to set your Google API keys:")
    
    # Get Google API key
    google_api_key = input("Enter your Google API key (or press Enter to skip): ").strip()
    if google_api_key:
        env_vars["GOOGLE_API_KEY"] = google_api_key
        print("✅ Google API key set")
    else:
        env_vars["GOOGLE_API_KEY"] = "your_google_api_key_here"
        print("⚠️ Google API key not set - you'll need to set it later")
    
    # Get Google Maps API key
    google_maps_key = input("Enter your Google Maps API key (or press Enter to skip): ").strip()
    if google_maps_key:
        env_vars["GOOGLE_MAPS_API_KEY"] = google_maps_key
        print("✅ Google Maps API key set")
    else:
        env_vars["GOOGLE_MAPS_API_KEY"] = "your_google_maps_api_key_here"
        print("⚠️ Google Maps API key not set - you'll need to set it later")
    
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    print("\n✅ Environment variables set!")
    print("\n📝 You can also create a .env file with these values:")
    print("(Note: .env files are blocked in this environment)")
    
    # Show .env content
    print("\nExample .env content:")
    print("-" * 40)
    for key, value in env_vars.items():
        print(f"{key}={value}")
    print("-" * 40)
    
    return env_vars

def test_configuration():
    """Test the configuration."""
    print("\n🧪 Testing configuration...")
    
    try:
        from config import Config
        
        # Test MongoDB connection
        if Config.validate_mongodb_connection():
            print("✅ MongoDB connection successful!")
        else:
            print("❌ MongoDB connection failed!")
            return False
        
        # Test environment variables
        required_vars = ["MONGODB_URI", "ERPNEXT_URL", "ERPNEXT_USERNAME"]
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing environment variables: {missing_vars}")
            return False
        
        print("✅ Configuration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def main():
    """Main setup function."""
    # Set up environment
    env_vars = setup_environment()
    
    # Test configuration
    if test_configuration():
        print("\n🎉 Environment setup completed successfully!")
        print("\n📝 Next steps:")
        print("1. Make sure your Google API keys are set correctly")
        print("2. Run: python aida_api_server.py")
        print("3. Open your browser to: http://localhost:5000")
    else:
        print("\n❌ Environment setup failed!")
        print("Please check your configuration and try again.")

if __name__ == "__main__":
    main() 