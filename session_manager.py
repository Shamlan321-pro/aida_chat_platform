import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import hashlib

# Import the new MongoDBManager
from mongodb_manager import MongoDBManager, UserSession

logger = logging.getLogger(__name__)

# SessionData is now replaced by UserSession from mongodb_manager
# Keep this alias for backward compatibility
SessionData = UserSession

class SessionManager:
    """Manages persistent sessions with credential storage and chat history using MongoDB."""
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/", db_name: str = "aida_platform", **kwargs):
        # Initialize the new MongoDBManager
        self.db_manager = MongoDBManager(mongo_uri, db_name)
        
        # Clean up expired sessions on startup
        self.db_manager.cleanup_expired_sessions()
        
        logger.info(f"MongoDB-based session storage initialized: {mongo_uri}")
    
    # These methods are now handled by MongoDBManager
    # Keep for backward compatibility but delegate to db_manager
    def _hash_credential(self, credential: str) -> str:
        """Hash credentials for secure storage."""
        return self.db_manager._hash_credential(credential)
    
    def _generate_browser_fingerprint(self, user_agent: str, ip_address: str) -> str:
        """Generate a simple browser fingerprint."""
        return self.db_manager._generate_browser_fingerprint(user_agent, ip_address)
    
    def create_session(self, erpnext_url: str, username: str, password: str, 
                      google_api_key: str, user_agent: str, ip_address: str,
                      site_base_url: str = None, user_id: str = None) -> str:
        """Create a new session with credentials."""
        return self.db_manager.create_session(
            erpnext_url=erpnext_url,
            username=username,
            password=password,
            google_api_key=google_api_key,
            user_agent=user_agent,
            ip_address=ip_address,
            site_base_url=site_base_url,
            user_id=user_id
        )
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session data."""
        return self.db_manager.get_session(session_id)
    
    def find_existing_session(self, user_agent: str, ip_address: str, 
                             erpnext_url: str, username: str, user_id: str = None) -> Optional[str]:
        """Find an existing session for the same user/browser combination."""
        return self.db_manager.find_existing_session(user_agent, ip_address, erpnext_url, username, user_id)
    
    def update_session_access(self, session_id: str):
        """Update the last accessed time for a session."""
        self.db_manager.update_session_access(session_id)
    
    def verify_credentials(self, session_id: str, password: str, google_api_key: str) -> bool:
        """Verify stored credentials against provided ones."""
        return self.db_manager.verify_credentials(session_id, password, google_api_key)
    
    def store_chat_message(self, session_id: str, user_message: str, ai_response: str,
                          query_result: Dict[str, Any] = None, doctype: str = None):
        """Store chat message in history."""
        # Store user message
        self.db_manager.store_chat_message(
            session_id=session_id,
            message_type="user",
            content=user_message,
            metadata={"query_result": query_result, "doctype": doctype} if query_result or doctype else None
        )
        
        # Store AI response
        self.db_manager.store_chat_message(
            session_id=session_id,
            message_type="assistant",
            content=ai_response,
            metadata={"query_result": query_result, "doctype": doctype} if query_result or doctype else None
        )
    
    def get_chat_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get chat history for session."""
        messages = self.db_manager.get_chat_history(session_id, limit)
        # MongoDBManager returns messages in the format expected by the UI
        # Each message has 'role' and 'content' fields
        return messages
    
    def cleanup_expired_sessions(self, days: int = 30):
        """Remove sessions older than specified days."""
        self.db_manager.cleanup_expired_sessions(days)
    
    def clear_all_sessions(self):
        """Clear all sessions and chat messages. Used on server restart."""
        self.db_manager.clear_all_sessions()
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return self.db_manager.get_database_stats()
    
    def close(self):
        """Close database connection."""
        self.db_manager.close()
    
    def get_recent_chats(self, user_id: str = None, user_identifier: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent chats for a user."""
        return self.db_manager.get_recent_chats(user_id=user_id, user_identifier=user_identifier, limit=limit)
    
    def get_chat_by_id(self, chat_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get a specific chat by ID."""
        return self.db_manager.get_chat_by_id(chat_id, user_id)
    
    def save_chat(self, session_id: str, title: str, preview: str, messages: List[Dict[str, Any]]) -> str:
        """Save a new chat."""
        return self.db_manager.save_chat(session_id, title, preview, messages)
    
    def delete_chat(self, chat_id: str, user_id: str = None) -> bool:
        """Delete a chat."""
        return self.db_manager.delete_chat(chat_id, user_id)