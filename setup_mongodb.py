#!/usr/bin/env python3
"""
MongoDB Setup Script for AIDA Platform
This script helps you install and configure MongoDB for the AIDA platform.
"""

import os
import sys
import subprocess
import platform
import requests
from pathlib import Path

def check_mongodb_installed() -> bool:
    """Check if MongoDB is installed and running."""
    try:
        # Try to connect to MongoDB
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
        
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
        client.admin.command('ismaster')
        client.close()
        print("✅ MongoDB is installed and running!")
        return True
    except Exception as e:
        print(f"❌ MongoDB not available: {e}")
        return False

def install_mongodb_windows():
    """Install MongoDB on Windows."""
    print("🔄 Installing MongoDB on Windows...")
    
    # Check if Chocolatey is installed
    try:
        subprocess.run(["choco", "--version"], check=True, capture_output=True)
        print("✅ Chocolatey found, using it to install MongoDB...")
        
        # Install MongoDB using Chocolatey
        subprocess.run(["choco", "install", "mongodb", "-y"], check=True)
        print("✅ MongoDB installed via Chocolatey")
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ Chocolatey not found. Please install MongoDB manually:")
        print("   1. Download from: https://www.mongodb.com/try/download/community")
        print("   2. Run the installer")
        print("   3. Start MongoDB service")
        return False
    
    return True

def install_mongodb_linux():
    """Install MongoDB on Linux."""
    print("🔄 Installing MongoDB on Linux...")
    
    # Detect package manager
    if os.path.exists("/etc/debian_version"):
        # Ubuntu/Debian
        print("📦 Installing MongoDB on Ubuntu/Debian...")
        try:
            # Add MongoDB GPG key
            subprocess.run(["wget", "-qO", "-", "https://www.mongodb.org/static/pgp/server-7.0.asc"], check=True)
            subprocess.run(["sudo", "apt-key", "add", "-"], check=True)
            
            # Add MongoDB repository
            echo_cmd = 'echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse"'
            subprocess.run(f"{echo_cmd} | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list", shell=True, check=True)
            
            # Update and install
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "mongodb-org"], check=True)
            
            # Start MongoDB service
            subprocess.run(["sudo", "systemctl", "start", "mongod"], check=True)
            subprocess.run(["sudo", "systemctl", "enable", "mongod"], check=True)
            
            print("✅ MongoDB installed and started on Ubuntu/Debian")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install MongoDB: {e}")
            return False
    
    elif os.path.exists("/etc/redhat-release"):
        # CentOS/RHEL
        print("📦 Installing MongoDB on CentOS/RHEL...")
        try:
            # Create MongoDB repo file
            repo_content = """[mongodb-org-7.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/\$releasever/mongodb-org/7.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-7.0.asc"""
            
            with open("/tmp/mongodb-org-7.0.repo", "w") as f:
                f.write(repo_content)
            
            subprocess.run(["sudo", "cp", "/tmp/mongodb-org-7.0.repo", "/etc/yum.repos.d/"], check=True)
            subprocess.run(["sudo", "yum", "install", "-y", "mongodb-org"], check=True)
            
            # Start MongoDB service
            subprocess.run(["sudo", "systemctl", "start", "mongod"], check=True)
            subprocess.run(["sudo", "systemctl", "enable", "mongod"], check=True)
            
            print("✅ MongoDB installed and started on CentOS/RHEL")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install MongoDB: {e}")
            return False
    
    else:
        print("⚠️ Unsupported Linux distribution. Please install MongoDB manually:")
        print("   https://docs.mongodb.com/manual/installation/")
        return False

def install_mongodb_macos():
    """Install MongoDB on macOS."""
    print("🔄 Installing MongoDB on macOS...")
    
    try:
        # Check if Homebrew is installed
        subprocess.run(["brew", "--version"], check=True, capture_output=True)
        print("✅ Homebrew found, using it to install MongoDB...")
        
        # Install MongoDB using Homebrew
        subprocess.run(["brew", "tap", "mongodb/brew"], check=True)
        subprocess.run(["brew", "install", "mongodb-community"], check=True)
        
        # Start MongoDB service
        subprocess.run(["brew", "services", "start", "mongodb-community"], check=True)
        
        print("✅ MongoDB installed and started on macOS")
        return True
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ Homebrew not found. Please install MongoDB manually:")
        print("   1. Install Homebrew: https://brew.sh/")
        print("   2. Run: brew tap mongodb/brew")
        print("   3. Run: brew install mongodb-community")
        print("   4. Run: brew services start mongodb-community")
        return False

def install_mongodb():
    """Install MongoDB based on the operating system."""
    system = platform.system().lower()
    
    if system == "windows":
        return install_mongodb_windows()
    elif system == "linux":
        return install_mongodb_linux()
    elif system == "darwin":
        return install_mongodb_macos()
    else:
        print(f"⚠️ Unsupported operating system: {system}")
        print("Please install MongoDB manually: https://docs.mongodb.com/manual/installation/")
        return False

def setup_mongodb_atlas():
    """Guide user through MongoDB Atlas setup."""
    print("\n🌐 MongoDB Atlas Setup (Cloud Option)")
    print("=" * 40)
    print("1. Go to https://www.mongodb.com/atlas")
    print("2. Create a free account")
    print("3. Create a new cluster (free tier)")
    print("4. Get your connection string")
    print("5. Set the MONGODB_URI environment variable")
    print("\nExample connection string:")
    print("mongodb+srv://username:password@cluster.mongodb.net/aida_platform")

def create_env_file():
    """Create a .env file with MongoDB configuration."""
    env_content = """# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_NAME=aida_platform
MONGODB_CONVERSATIONS_DB=aida_ai_conversations

# ERPNext Configuration
ERPNEXT_URL=http://localhost:8000
ERPNEXT_USERNAME=Administrator
ERPNEXT_PASSWORD=admin

# Google API Configuration
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key_here
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=False

# Session Configuration
SESSION_EXPIRY_DAYS=30

# Logging Configuration
LOG_LEVEL=INFO
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✅ Created .env file with default configuration")
    print("📝 Please update the values in .env file with your actual configuration")

def main():
    """Main setup function."""
    print("🚀 AIDA Platform - MongoDB Setup")
    print("=" * 40)
    
    # Check if MongoDB is already installed
    if check_mongodb_installed():
        print("✅ MongoDB is ready to use!")
        create_env_file()
        return
    
    # Ask user for installation method
    print("\n📋 MongoDB Installation Options:")
    print("1. Install MongoDB locally")
    print("2. Use MongoDB Atlas (cloud)")
    print("3. Skip (manual installation)")
    
    choice = input("\nSelect an option (1-3): ").strip()
    
    if choice == "1":
        print("\n🔄 Installing MongoDB locally...")
        if install_mongodb():
            print("✅ MongoDB installation completed!")
            create_env_file()
        else:
            print("❌ MongoDB installation failed. Please install manually.")
    
    elif choice == "2":
        setup_mongodb_atlas()
        create_env_file()
    
    elif choice == "3":
        print("ℹ️ Skipping MongoDB installation.")
        print("Please install MongoDB manually and update the .env file.")
        create_env_file()
    
    else:
        print("❌ Invalid choice. Please run the script again.")
        return
    
    print("\n🎉 Setup completed!")
    print("\n📝 Next steps:")
    print("1. Update the .env file with your configuration")
    print("2. Run: python migrate_to_mongodb.py (if you have existing SQLite data)")
    print("3. Run: python aida_api_server.py")

if __name__ == "__main__":
    main() 