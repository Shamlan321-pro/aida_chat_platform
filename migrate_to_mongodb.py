#!/usr/bin/env python3
"""
Migration script to move from SQLite to MongoDB for AIDA Platform.
This script will migrate existing sessions and chat history from SQLite to MongoDB.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from mongodb_manager import MongoDBManager
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SQLiteToMongoDBMigrator:
    """Migrate data from SQLite to MongoDB."""
    
    def __init__(self, sqlite_db_path: str = "aida_database.db", mongo_uri: str = None, mongo_db_name: str = None):
        self.sqlite_db_path = sqlite_db_path
        self.mongo_uri = mongo_uri or Config.MONGODB_URI
        self.mongo_db_name = mongo_db_name or Config.MONGODB_DB_NAME
        
        # Initialize MongoDB manager
        self.mongo_manager = MongoDBManager(self.mongo_uri, self.mongo_db_name)
        
        # SQLite connection
        self.sqlite_conn = None
    
    def _connect_sqlite(self):
        """Connect to SQLite database."""
        try:
            self.sqlite_conn = sqlite3.connect(self.sqlite_db_path)
            logger.info(f"✅ Connected to SQLite database: {self.sqlite_db_path}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to SQLite: {e}")
            raise Exception(f"SQLite connection failed: {e}")
    
    def _check_sqlite_data(self) -> Dict[str, int]:
        """Check what data exists in SQLite."""
        if not self.sqlite_conn:
            self._connect_sqlite()
        
        cursor = self.sqlite_conn.cursor()
        
        # Count sessions
        cursor.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]
        
        # Count messages
        cursor.execute("SELECT COUNT(*) FROM chat_messages")
        message_count = cursor.fetchone()[0]
        
        return {
            "sessions": session_count,
            "messages": message_count
        }
    
    def _migrate_sessions(self) -> int:
        """Migrate sessions from SQLite to MongoDB."""
        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE is_active = 1")
        
        migrated_count = 0
        for row in cursor.fetchall():
            try:
                # Convert SQLite row to session data
                session_data = {
                    "session_id": row[0],
                    "user_identifier": row[1],
                    "erpnext_url": row[2],
                    "username": row[3],
                    "password_hash": row[4],
                    "google_api_key_hash": row[5],
                    "site_base_url": row[6],
                    "created_at": datetime.fromisoformat(row[7]),
                    "last_accessed": datetime.fromisoformat(row[8]),
                    "browser_fingerprint": row[9],
                    "is_active": bool(row[10])
                }
                
                # Insert into MongoDB
                self.mongo_manager.sessions_collection.insert_one(session_data)
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to migrate session {row[0]}: {e}")
        
        logger.info(f"✅ Migrated {migrated_count} sessions")
        return migrated_count
    
    def _migrate_messages(self) -> int:
        """Migrate chat messages from SQLite to MongoDB."""
        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT * FROM chat_messages ORDER BY timestamp")
        
        migrated_count = 0
        for row in cursor.fetchall():
            try:
                # Convert SQLite row to message data
                message_data = {
                    "message_id": row[0],
                    "session_id": row[1],
                    "user_identifier": row[2],
                    "timestamp": datetime.fromisoformat(row[3]),
                    "message_type": row[4],
                    "content": row[5],
                    "metadata": json.loads(row[6]) if row[6] else None
                }
                
                # Insert into MongoDB
                self.mongo_manager.messages_collection.insert_one(message_data)
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to migrate message {row[0]}: {e}")
        
        logger.info(f"✅ Migrated {migrated_count} messages")
        return migrated_count
    
    def migrate(self) -> Dict[str, int]:
        """Perform the complete migration."""
        logger.info("🚀 Starting SQLite to MongoDB migration...")
        
        # Check if SQLite database exists
        import os
        if not os.path.exists(self.sqlite_db_path):
            logger.warning(f"⚠️ SQLite database not found: {self.sqlite_db_path}")
            return {"sessions": 0, "messages": 0}
        
        # Connect to SQLite
        self._connect_sqlite()
        
        # Check existing data
        data_counts = self._check_sqlite_data()
        logger.info(f"📊 Found in SQLite: {data_counts['sessions']} sessions, {data_counts['messages']} messages")
        
        if data_counts['sessions'] == 0 and data_counts['messages'] == 0:
            logger.info("ℹ️ No data to migrate")
            return data_counts
        
        # Perform migration
        try:
            sessions_migrated = self._migrate_sessions()
            messages_migrated = self._migrate_messages()
            
            logger.info("✅ Migration completed successfully!")
            return {
                "sessions": sessions_migrated,
                "messages": messages_migrated
            }
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise Exception(f"Migration failed: {e}")
        
        finally:
            if self.sqlite_conn:
                self.sqlite_conn.close()
    
    def verify_migration(self) -> bool:
        """Verify that migration was successful."""
        try:
            # Get counts from both databases
            sqlite_counts = self._check_sqlite_data()
            
            # Get MongoDB counts
            mongo_sessions = self.mongo_manager.sessions_collection.count_documents({})
            mongo_messages = self.mongo_manager.messages_collection.count_documents({})
            
            logger.info(f"📊 Verification:")
            logger.info(f"  SQLite: {sqlite_counts['sessions']} sessions, {sqlite_counts['messages']} messages")
            logger.info(f"  MongoDB: {mongo_sessions} sessions, {mongo_messages} messages")
            
            # Check if all data was migrated
            if mongo_sessions >= sqlite_counts['sessions'] and mongo_messages >= sqlite_counts['messages']:
                logger.info("✅ Migration verification successful!")
                return True
            else:
                logger.warning("⚠️ Migration verification failed - some data may be missing")
                return False
                
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False

def main():
    """Main migration function."""
    import os
    
    print("🔄 AIDA Platform - SQLite to MongoDB Migration")
    print("=" * 50)
    
    # Check MongoDB connection
    if not Config.validate_mongodb_connection():
        print("❌ MongoDB connection failed. Please ensure MongoDB is running.")
        return
    
    # Initialize migrator
    migrator = SQLiteToMongoDBMigrator()
    
    # Perform migration
    try:
        results = migrator.migrate()
        
        if results['sessions'] > 0 or results['messages'] > 0:
            print(f"✅ Migration completed: {results['sessions']} sessions, {results['messages']} messages")
            
            # Verify migration
            if migrator.verify_migration():
                print("✅ Migration verification successful!")
                
                # Ask if user wants to backup old SQLite file
                backup = input("\n💾 Would you like to backup the old SQLite database? (y/n): ").lower().strip()
                if backup == 'y':
                    backup_path = f"aida_database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    import shutil
                    shutil.copy2("aida_database.db", backup_path)
                    print(f"✅ Backup created: {backup_path}")
            else:
                print("⚠️ Migration verification failed. Please check the logs.")
        else:
            print("ℹ️ No data to migrate")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return
    
    print("\n🎉 Migration process completed!")
    print("You can now remove the old SQLite database if desired.")

if __name__ == "__main__":
    main() 