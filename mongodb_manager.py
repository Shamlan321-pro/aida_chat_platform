import json
import uuid
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import os

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, DuplicateKeyError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    print("⚠️ MongoDB not available. Install with: pip install pymongo")

logger = logging.getLogger(__name__)

@dataclass
class UserSession:
    """Data class for user session information."""
    session_id: str
    user_identifier: str  # Combination of username + erpnext_url (for backward compatibility)
    erpnext_url: str
    username: str
    password_hash: str
    google_api_key_hash: str
    site_base_url: str
    created_at: datetime
    last_accessed: datetime
    browser_fingerprint: str
    user_id: Optional[str] = None  # User ID from authentication system (optional for backward compatibility)
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['created_at'] = self.created_at
        data['last_accessed'] = self.last_accessed
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        """Create UserSession from dictionary."""
        # Remove MongoDB-specific fields
        if '_id' in data:
            del data['_id']
        return cls(**data)

@dataclass
class ChatMessage:
    """Data class for chat messages."""
    message_id: str
    session_id: str
    user_identifier: str  # Combination of username + erpnext_url (for backward compatibility)
    timestamp: datetime
    message_type: str  # 'user' or 'assistant'
    content: str
    user_id: Optional[str] = None  # User ID from authentication system (optional for backward compatibility)
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['timestamp'] = self.timestamp
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create ChatMessage from dictionary."""
        return cls(**data)

class MongoDBManager:
    """MongoDB-based database manager for multi-user, multi-instance chat history."""
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/", db_name: str = "aida_platform"):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self.sessions_collection = None
        self.messages_collection = None
        
        if not MONGODB_AVAILABLE:
            raise ImportError("PyMongo not available. Install with: pip install pymongo")
        
        self._connect()
        self._init_collections()
        logger.info(f"MongoDB-based session storage initialized: {mongo_uri}")
    
    def _connect(self):
        """Connect to MongoDB with error handling."""
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ismaster')
            self.db = self.client[self.db_name]
            logger.info("✅ MongoDB connection established successfully")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise Exception(f"MongoDB connection failed: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected MongoDB error: {e}")
            raise Exception(f"MongoDB setup failed: {e}")
    
    def _init_collections(self):
        """Initialize collections and create indexes."""
        try:
            # Initialize collections
            self.sessions_collection = self.db.sessions
            self.messages_collection = self.db.chat_messages
            
            # Create indexes for better performance
            # Sessions indexes
            self.sessions_collection.create_index([("user_identifier", 1)])
            self.sessions_collection.create_index([("last_accessed", -1)])
            self.sessions_collection.create_index([("browser_fingerprint", 1)])
            self.sessions_collection.create_index([("is_active", 1)])
            
            # Messages indexes
            self.messages_collection.create_index([("session_id", 1)])
            self.messages_collection.create_index([("user_identifier", 1)])
            self.messages_collection.create_index([("timestamp", -1)])
            self.messages_collection.create_index([("message_type", 1)])
            
            # Chats collection and indexes
            self.chats_collection = self.db.chats
            self.chats_collection.create_index([("user_identifier", 1)])
            self.chats_collection.create_index([("session_id", 1)])
            self.chats_collection.create_index([("created_at", -1)])
            self.chats_collection.create_index([("chat_id", 1)])
            
            logger.info("✅ MongoDB collections and indexes initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize collections: {e}")
            raise Exception(f"Collection initialization failed: {e}")
    
    def _generate_user_identifier(self, username: str, erpnext_url: str) -> str:
        """Generate unique identifier for user+instance combination."""
        # Normalize URL to avoid duplicates
        normalized_url = erpnext_url.rstrip('/').lower()
        identifier_string = f"{username.lower()}@{normalized_url}"
        return hashlib.sha256(identifier_string.encode()).hexdigest()[:16]
    
    def _hash_credential(self, credential: str) -> str:
        """Hash credentials for secure storage."""
        return hashlib.sha256(credential.encode()).hexdigest()
    
    def _generate_browser_fingerprint(self, user_agent: str, ip_address: str) -> str:
        """Generate a simple browser fingerprint."""
        fingerprint_data = f"{user_agent}:{ip_address}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    def create_session(self, erpnext_url: str, username: str, password: str,
                      google_api_key: str, user_agent: str, ip_address: str,
                      site_base_url: str = None, user_id: str = None) -> str:
        """Create a new user session."""
        session_id = str(uuid.uuid4())
        user_identifier = self._generate_user_identifier(username, erpnext_url)
        browser_fingerprint = self._generate_browser_fingerprint(user_agent, ip_address)
        now = datetime.now()
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,  # User ID from authentication system (can be None)
            "user_identifier": user_identifier,
            "erpnext_url": erpnext_url,
            "username": username,
            "password_hash": self._hash_credential(password),
            "google_api_key_hash": self._hash_credential(google_api_key),
            "site_base_url": site_base_url or erpnext_url,
            "created_at": now,
            "last_accessed": now,
            "browser_fingerprint": browser_fingerprint,
            "is_active": True
        }
        
        try:
            result = self.sessions_collection.insert_one(session_data)
            logger.info(f"✅ Created new session {session_id} for user {username} (ID: {user_id}) on {erpnext_url}")
            return session_id
        except DuplicateKeyError:
            logger.warning(f"Session {session_id} already exists, generating new ID")
            return self.create_session(erpnext_url, username, password, google_api_key, user_agent, ip_address, site_base_url, user_id)
        except Exception as e:
            logger.error(f"❌ Failed to create session: {e}")
            raise Exception(f"Session creation failed: {e}")
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Retrieve session data by session ID."""
        try:
            session_data = self.sessions_collection.find_one({
                "session_id": session_id,
                "is_active": True
            })
            
            if session_data:
                # Convert MongoDB document to UserSession
                session_data['_id'] = str(session_data['_id'])  # Convert ObjectId to string
                return UserSession.from_dict(session_data)
            
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get session {session_id}: {e}")
            return None
    
    def find_existing_session(self, user_agent: str, ip_address: str,
                             erpnext_url: str, username: str, user_id: str = None) -> Optional[str]:
        """Find existing active session for user+instance combination."""
        user_identifier = self._generate_user_identifier(username, erpnext_url)
        browser_fingerprint = self._generate_browser_fingerprint(user_agent, ip_address)
        cutoff_date = datetime.now() - timedelta(days=30)
        
        try:
            # First try to find by user_id if provided
            if user_id:
                session_data = self.sessions_collection.find_one({
                    "user_id": user_id,
                    "erpnext_url": erpnext_url,
                    "last_accessed": {"$gte": cutoff_date},
                    "is_active": True
                }, sort=[("last_accessed", -1)])
                
                if session_data:
                    logger.info(f"✅ Found existing session by user_id: {session_data.get('session_id')}")
                    return session_data.get("session_id")
            
            # Fallback to user_identifier and browser fingerprint
            session_data = self.sessions_collection.find_one({
                "user_identifier": user_identifier,
                "browser_fingerprint": browser_fingerprint,
                "last_accessed": {"$gte": cutoff_date},
                "is_active": True
            }, sort=[("last_accessed", -1)])
            
            if session_data:
                logger.info(f"✅ Found existing session by user_identifier: {session_data.get('session_id')}")
                return session_data.get("session_id")
            
            logger.info(f"❌ No existing session found for user_id: {user_id}, user_identifier: {user_identifier}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to find existing session: {e}")
            return None
    
    def update_session_access(self, session_id: str):
        """Update last accessed time for session."""
        try:
            self.sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": {"last_accessed": datetime.now()}}
            )
        except Exception as e:
            logger.error(f"❌ Failed to update session access: {e}")
    
    def verify_credentials(self, session_id: str, password: str, google_api_key: str) -> bool:
        """Verify stored credentials match provided ones."""
        session = self.get_session(session_id)
        if not session:
            return False
        
        password_hash = self._hash_credential(password)
        api_key_hash = self._hash_credential(google_api_key)
        
        return (session.password_hash == password_hash and 
                session.google_api_key_hash == api_key_hash)
    
    def store_chat_message(self, session_id: str, message_type: str, content: str,
                          metadata: Dict[str, Any] = None) -> str:
        """Store a chat message."""
        # Get session to get user_identifier and user_id
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        message_id = str(uuid.uuid4())
        message_data = {
            "message_id": message_id,
            "session_id": session_id,
            "user_id": session.user_id,  # User ID from authentication system
            "user_identifier": session.user_identifier,
            "timestamp": datetime.now(),
            "message_type": message_type,
            "content": content,
            "metadata": metadata
        }
        
        try:
            result = self.messages_collection.insert_one(message_data)
            logger.debug(f"✅ Stored {message_type} message for session {session_id} (user_id: {session.user_id})")
            return message_id
        except Exception as e:
            logger.error(f"❌ Failed to store message: {e}")
            raise Exception(f"Message storage failed: {e}")
    
    def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        try:
            cursor = self.messages_collection.find(
                {"session_id": session_id}
            ).sort("timestamp", 1).limit(limit)
            
            messages = []
            for doc in cursor:
                messages.append({
                    'role': 'user' if doc['message_type'] == 'user' else 'assistant',
                    'content': doc['content'],
                    'timestamp': doc['timestamp'].isoformat(),
                    'metadata': doc.get('metadata')
                })
            
            return messages
        except Exception as e:
            logger.error(f"❌ Failed to get chat history: {e}")
            return []
    
    def get_user_chat_history(self, username: str, erpnext_url: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all chat history for a user across all sessions on a specific ERPNext instance."""
        user_identifier = self._generate_user_identifier(username, erpnext_url)
        
        try:
            cursor = self.messages_collection.find(
                {"user_identifier": user_identifier}
            ).sort("timestamp", -1).limit(limit)
            
            messages = []
            for doc in cursor:
                messages.append({
                    'session_id': doc['session_id'],
                    'role': 'user' if doc['message_type'] == 'user' else 'assistant',
                    'content': doc['content'],
                    'timestamp': doc['timestamp'].isoformat(),
                    'metadata': doc.get('metadata')
                })
            
            return messages
        except Exception as e:
            logger.error(f"❌ Failed to get user chat history: {e}")
            return []
    
    def deactivate_session(self, session_id: str):
        """Deactivate a session (soft delete)."""
        try:
            self.sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": {"is_active": False}}
            )
            logger.info(f"✅ Deactivated session {session_id}")
        except Exception as e:
            logger.error(f"❌ Failed to deactivate session: {e}")
    
    def cleanup_expired_sessions(self, days: int = 30):
        """Clean up expired sessions and their messages."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            # Find expired sessions
            expired_sessions = list(self.sessions_collection.find({
                "$or": [
                    {"last_accessed": {"$lt": cutoff_date}},
                    {"is_active": False}
                ]
            }, {"session_id": 1}))
            
            if expired_sessions:
                session_ids = [s["session_id"] for s in expired_sessions]
                
                # Delete messages for expired sessions
                messages_result = self.messages_collection.delete_many({
                    "session_id": {"$in": session_ids}
                })
                
                # Delete expired sessions
                sessions_result = self.sessions_collection.delete_many({
                    "session_id": {"$in": session_ids}
                })
                
                logger.info(f"✅ Cleaned up {len(session_ids)} expired sessions and {messages_result.deleted_count} messages")
        except Exception as e:
            logger.error(f"❌ Failed to cleanup expired sessions: {e}")
    
    def clear_all_sessions(self):
        """Clear all sessions and chat messages. Used on server restart."""
        try:
            # Delete all messages first
            messages_result = self.messages_collection.delete_many({})
            
            # Delete all sessions
            sessions_result = self.sessions_collection.delete_many({})
            
            logger.info(f"✅ Cleared all sessions ({sessions_result.deleted_count}) and messages ({messages_result.deleted_count})")
        except Exception as e:
            logger.error(f"❌ Failed to clear all sessions: {e}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            # Count active sessions
            active_sessions = self.sessions_collection.count_documents({"is_active": True})
            
            # Count total messages
            total_messages = self.messages_collection.count_documents({})
            
            # Count unique users
            unique_users = len(self.sessions_collection.distinct("user_identifier"))
            
            # Get database size (approximate)
            db_stats = self.db.command("dbStats")
            db_size_bytes = db_stats.get("dataSize", 0)
            
            return {
                'active_sessions': active_sessions,
                'total_messages': total_messages,
                'unique_users': unique_users,
                'database_size_bytes': db_size_bytes,
                'database_size_mb': round(db_size_bytes / (1024 * 1024), 2)
            }
        except Exception as e:
            logger.error(f"❌ Failed to get database stats: {e}")
            return {
                'active_sessions': 0,
                'total_messages': 0,
                'unique_users': 0,
                'database_size_bytes': 0,
                'database_size_mb': 0
            }
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("✅ MongoDB connection closed")
    
    def get_recent_chats(self, user_id: str = None, user_identifier: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent chats for a user."""
        try:
            # Use user_id if provided, otherwise fallback to user_identifier
            if user_id:
                cursor = self.db.chats.find(
                    {"user_id": user_id}
                ).sort("created_at", -1).limit(limit)
            elif user_identifier:
                cursor = self.db.chats.find(
                    {"user_identifier": user_identifier}
                ).sort("created_at", -1).limit(limit)
            else:
                logger.error("❌ No user_id or user_identifier provided")
                return []
            
            chats = []
            for doc in cursor:
                chats.append({
                    "chat_id": doc["chat_id"],
                    "title": doc["title"],
                    "preview": doc["preview"],
                    "created_at": doc["created_at"].isoformat(),
                    "message_count": len(doc.get("messages", []))
                })
            
            return chats
        except Exception as e:
            logger.error(f"❌ Failed to get recent chats: {e}")
            return []
    
    def get_chat_by_id(self, chat_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get a specific chat by ID."""
        try:
            # If user_id is provided, ensure the chat belongs to that user
            if user_id:
                chat = self.db.chats.find_one({"chat_id": chat_id, "user_id": user_id})
            else:
                chat = self.db.chats.find_one({"chat_id": chat_id})
                
            if chat:
                return {
                    "chat_id": chat["chat_id"],
                    "title": chat["title"],
                    "preview": chat["preview"],
                    "created_at": chat["created_at"].isoformat(),
                    "messages": chat.get("messages", [])
                }
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get chat: {e}")
            return None
    
    def save_chat(self, session_id: str, title: str, preview: str, messages: List[Dict[str, Any]]) -> str:
        """Save a new chat."""
        try:
            chat_id = str(uuid.uuid4())
            
            # Get session to get user_identifier and user_id
            session = self.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            chat_data = {
                "chat_id": chat_id,
                "session_id": session_id,
                "user_id": session.user_id,  # User ID from authentication system
                "user_identifier": session.user_identifier,
                "title": title,
                "preview": preview,
                "messages": messages,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            self.db.chats.insert_one(chat_data)
            logger.info(f"✅ Saved chat: {chat_id} for user_id: {session.user_id}")
            return chat_id
        except Exception as e:
            logger.error(f"❌ Failed to save chat: {e}")
            raise Exception(f"Chat save failed: {e}")
    
    def delete_chat(self, chat_id: str, user_id: str = None) -> bool:
        """Delete a chat."""
        try:
            # If user_id is provided, ensure the chat belongs to that user
            if user_id:
                result = self.db.chats.delete_one({"chat_id": chat_id, "user_id": user_id})
            else:
                result = self.db.chats.delete_one({"chat_id": chat_id})
                
            if result.deleted_count > 0:
                logger.info(f"✅ Deleted chat: {chat_id} for user_id: {user_id}")
                return True
            else:
                logger.warning(f"⚠️ Chat not found: {chat_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to delete chat: {e}")
            return False 