# MongoDB Migration Guide for AIDA Platform

This guide will help you migrate from SQLite to MongoDB for the AIDA Platform.

## 🎯 Overview

The AIDA Platform has been updated to use MongoDB as the primary database instead of SQLite. This provides:

- **Better scalability** for multi-user environments
- **Improved performance** for large datasets
- **Better support** for complex queries and indexing
- **Cloud-ready** architecture with MongoDB Atlas support

## 📋 Prerequisites

1. **Python 3.8+** installed
2. **PyMongo** driver (already installed: `pip install pymongo`)
3. **MongoDB** server (local or cloud)

## 🚀 Quick Setup

### Option 1: Automated Setup (Recommended)

Run the setup script:

```bash
python setup_mongodb.py
```

This script will:
- Check if MongoDB is installed
- Guide you through installation if needed
- Create a `.env` file with proper configuration
- Help you choose between local MongoDB or MongoDB Atlas

### Option 2: Manual Setup

#### Local MongoDB Installation

**Windows:**
1. Download MongoDB Community Server from: https://www.mongodb.com/try/download/community
2. Run the installer
3. Start MongoDB service

**macOS:**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**Ubuntu/Debian:**
```bash
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod
```

#### MongoDB Atlas (Cloud)

1. Go to https://www.mongodb.com/atlas
2. Create a free account
3. Create a new cluster (free tier)
4. Get your connection string
5. Update the `MONGODB_URI` in your `.env` file

## ⚙️ Configuration

Create a `.env` file with the following configuration:

```env
# MongoDB Configuration
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
```

## 🔄 Migration Process

### Step 1: Backup Existing Data (Optional)

If you have existing SQLite data, backup the database:

```bash
cp aida_database.db aida_database_backup.db
```

### Step 2: Run Migration Script

```bash
python migrate_to_mongodb.py
```

This script will:
- Connect to your existing SQLite database
- Migrate all sessions and chat history to MongoDB
- Verify the migration was successful
- Optionally create a backup of the old SQLite file

### Step 3: Verify Migration

The migration script will automatically verify the data transfer. You can also manually check:

```python
from mongodb_manager import MongoDBManager

# Initialize MongoDB manager
mongo_manager = MongoDBManager()

# Get database statistics
stats = mongo_manager.get_database_stats()
print(f"Active sessions: {stats['active_sessions']}")
print(f"Total messages: {stats['total_messages']}")
print(f"Unique users: {stats['unique_users']}")
```

## 🧪 Testing the Migration

### Test MongoDB Connection

```python
from config import Config

# Test MongoDB connection
if Config.validate_mongodb_connection():
    print("✅ MongoDB connection successful!")
else:
    print("❌ MongoDB connection failed!")
```

### Test Session Management

```python
from session_manager import SessionManager

# Initialize session manager
session_manager = SessionManager()

# Test session creation
session_id = session_manager.create_session(
    erpnext_url="http://localhost:8000",
    username="test_user",
    password="test_password",
    google_api_key="test_key",
    user_agent="test_agent",
    ip_address="127.0.0.1"
)

print(f"✅ Created session: {session_id}")
```

## 🚀 Running the Application

After migration, start the application normally:

```bash
python aida_api_server.py
```

The application will now use MongoDB for all data storage.

## 📊 Database Schema

### Sessions Collection
```javascript
{
  "_id": ObjectId,
  "session_id": "uuid-string",
  "user_identifier": "hash-of-username-url",
  "erpnext_url": "http://localhost:8000",
  "username": "user@example.com",
  "password_hash": "sha256-hash",
  "google_api_key_hash": "sha256-hash",
  "site_base_url": "http://localhost:8000",
  "created_at": ISODate,
  "last_accessed": ISODate,
  "browser_fingerprint": "md5-hash",
  "is_active": true
}
```

### Chat Messages Collection
```javascript
{
  "_id": ObjectId,
  "message_id": "uuid-string",
  "session_id": "uuid-string",
  "user_identifier": "hash-of-username-url",
  "timestamp": ISODate,
  "message_type": "user|assistant",
  "content": "message content",
  "metadata": {
    "query_result": {...},
    "doctype": "Lead"
  }
}
```

### Conversations Collection (AI Memory)
```javascript
{
  "_id": ObjectId,
  "session_id": "uuid-string",
  "timestamp": ISODate,
  "user_message": "user input",
  "ai_response": "ai response",
  "query_result": {...},
  "doctype": "Lead"
}
```

## 🔧 Troubleshooting

### MongoDB Connection Issues

1. **Check if MongoDB is running:**
   ```bash
   # Windows
   net start MongoDB
   
   # Linux/macOS
   sudo systemctl status mongod
   ```

2. **Check MongoDB port:**
   ```bash
   netstat -an | grep 27017
   ```

3. **Test connection manually:**
   ```python
   from pymongo import MongoClient
   client = MongoClient("mongodb://localhost:27017/")
   client.admin.command('ismaster')
   ```

### Migration Issues

1. **Check SQLite database exists:**
   ```bash
   ls -la aida_database.db
   ```

2. **Verify MongoDB is accessible:**
   ```python
   from config import Config
   Config.validate_mongodb_connection()
   ```

3. **Check migration logs:**
   The migration script provides detailed logging of the process.

### Performance Issues

1. **Create indexes (automatic):**
   The MongoDB manager automatically creates necessary indexes.

2. **Monitor database size:**
   ```python
   stats = mongo_manager.get_database_stats()
   print(f"Database size: {stats['database_size_mb']} MB")
   ```

## 🔄 Rollback (If Needed)

If you need to rollback to SQLite:

1. **Stop the application**
2. **Restore SQLite database:**
   ```bash
   cp aida_database_backup.db aida_database.db
   ```
3. **Revert code changes** (restore old `session_manager.py` and `database_manager.py`)
4. **Restart application**

## 📈 Benefits of MongoDB

1. **Scalability**: Handles multiple users and large datasets better
2. **Performance**: Better indexing and query performance
3. **Flexibility**: Schema-less design allows for easy data structure changes
4. **Cloud Ready**: Easy migration to MongoDB Atlas for production
5. **Monitoring**: Better tools for monitoring and analytics
6. **Backup**: Built-in backup and restore capabilities

## 🆘 Support

If you encounter issues:

1. Check the logs for detailed error messages
2. Verify MongoDB connection and permissions
3. Ensure all environment variables are set correctly
4. Test with the provided test scripts

For additional help, check the MongoDB documentation: https://docs.mongodb.com/ 