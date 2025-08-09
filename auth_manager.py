#!/usr/bin/env python3
"""
Authentication Manager for AIDA Platform
Handles user authentication, admin functions, and user management
"""

import hashlib
import secrets
import string
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import logging

logger = logging.getLogger(__name__)

@dataclass
class User:
    """User data class"""
    user_id: str
    username: str
    email: str
    password_hash: str
    role: str  # 'admin' or 'user'
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    mocxha_credentials: Optional[Dict] = None
    profile_data: Optional[Dict] = None

@dataclass
class UserSession:
    """User session data class"""
    session_id: str
    user_id: str
    username: str
    created_at: datetime
    last_activity: datetime
    is_active: bool
    ip_address: str
    user_agent: str

class AuthManager:
    """Authentication and user management system"""
    
    def __init__(self, mongo_uri: str, db_name: str):
        """Initialize authentication manager"""
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self.users_collection = None
        self.sessions_collection = None
        self._connect()
        self._init_collections()
        self._ensure_admin_exists()
    
    def _connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            logger.info("✅ Connected to MongoDB for authentication")
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    def _init_collections(self):
        """Initialize collections and indexes"""
        try:
            # Users collection
            self.users_collection = self.db.users
            self.users_collection.create_index("username", unique=True)
            self.users_collection.create_index("email", unique=True)
            self.users_collection.create_index("user_id", unique=True)
            
            # Sessions collection
            self.sessions_collection = self.db.user_sessions
            self.sessions_collection.create_index("session_id", unique=True)
            self.sessions_collection.create_index("user_id")
            self.sessions_collection.create_index("created_at", expireAfterSeconds=86400*7)  # 7 days TTL
            
            logger.info("✅ Authentication collections initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize collections: {e}")
            raise
    
    def _ensure_admin_exists(self):
        """Ensure admin user exists"""
        try:
            # Check if admin user exists with the correct username
            admin_user = self.users_collection.find_one({"username": "Shamlan321", "role": "admin"})
            
            if not admin_user:
                # Check if any admin user exists (might have different username)
                existing_admin = self.users_collection.find_one({"role": "admin"})
                
                if existing_admin:
                    # Remove the old admin user
                    self.users_collection.delete_one({"_id": existing_admin["_id"]})
                    logger.info("✅ Removed old admin user")
                
                # Check if Shamlan321 username exists (might be a regular user)
                existing_user = self.users_collection.find_one({"username": "Shamlan321"})
                if existing_user:
                    # Remove the existing user with Shamlan321 username
                    self.users_collection.delete_one({"_id": existing_user["_id"]})
                    logger.info("✅ Removed existing user with Shamlan321 username")
                
                # Create new admin user with specified credentials
                admin_user = User(
                    user_id="admin_001",
                    username="Shamlan321",
                    email="admin@aida-platform.com",
                    password_hash=self._hash_password("5h4ml4n321"),  # Specified password
                    role="admin",
                    is_active=True,
                    created_at=datetime.now(),
                    last_login=None
                )
                self._save_user(admin_user)
                logger.info(f"✅ Created admin user with credentials: Shamlan321/5h4ml4n321")
            else:
                # Admin user exists with correct username, update password if needed
                current_password_hash = admin_user.get("password_hash")
                expected_password_hash = self._hash_password("5h4ml4n321")
                
                if current_password_hash != expected_password_hash:
                    # Update password
                    self.users_collection.update_one(
                        {"_id": admin_user["_id"]},
                        {"$set": {"password_hash": expected_password_hash}}
                    )
                    logger.info(f"✅ Updated admin user password to: 5h4ml4n321")
                else:
                    logger.info("✅ Admin user already exists with correct credentials")
                    
        except Exception as e:
            logger.error(f"❌ Failed to ensure admin exists: {e}")
            raise
    
    def _generate_password(self, length: int = 12) -> str:
        """Generate a random password"""
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return self._hash_password(password) == password_hash
    
    def _save_user(self, user: User):
        """Save user to database"""
        user_dict = {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "password_hash": user.password_hash,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "mocxha_credentials": user.mocxha_credentials,
            "profile_data": user.profile_data
        }
        self.users_collection.insert_one(user_dict)
    
    def _user_from_dict(self, data: Dict) -> User:
        """Create User object from dictionary"""
        # Remove MongoDB-specific fields
        if '_id' in data:
            del data['_id']
        return User(
            user_id=data["user_id"],
            username=data["username"],
            email=data["email"],
            password_hash=data["password_hash"],
            role=data["role"],
            is_active=data["is_active"],
            created_at=data["created_at"],
            last_login=data.get("last_login"),
            mocxha_credentials=data.get("mocxha_credentials"),
            profile_data=data.get("profile_data")
        )
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[User], str]:
        """Authenticate user with username and password"""
        try:
            user_data = self.users_collection.find_one({"username": username})
            if not user_data:
                return False, None, "Invalid username or password"
            
            user = self._user_from_dict(user_data)
            
            if not user.is_active:
                return False, None, "Account is deactivated"
            
            if not self._verify_password(password, user.password_hash):
                return False, None, "Invalid username or password"
            
            # Update last login
            self.users_collection.update_one(
                {"user_id": user.user_id},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            
            return True, user, "Authentication successful"
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False, None, "Authentication failed"
    
    def create_user_session(self, user: User, ip_address: str, user_agent: str) -> str:
        """Create a new user session"""
        try:
            session_id = secrets.token_urlsafe(32)
            session = UserSession(
                session_id=session_id,
                user_id=user.user_id,
                username=user.username,
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                is_active=True,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            session_dict = {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "username": session.username,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "is_active": session.is_active,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent
            }
            
            self.sessions_collection.insert_one(session_dict)
            logger.info(f"✅ Session created for user: {user.username}")
            return session_id
        except Exception as e:
            logger.error(f"❌ Failed to create session: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID"""
        try:
            session_data = self.sessions_collection.find_one({"session_id": session_id, "is_active": True})
            if not session_data:
                return None
            
            return UserSession(
                session_id=session_data["session_id"],
                user_id=session_data["user_id"],
                username=session_data["username"],
                created_at=session_data["created_at"],
                last_activity=session_data["last_activity"],
                is_active=session_data["is_active"],
                ip_address=session_data["ip_address"],
                user_agent=session_data["user_agent"]
            )
        except Exception as e:
            logger.error(f"❌ Failed to get session: {e}")
            return None
    
    def update_session_activity(self, session_id: str):
        """Update session last activity"""
        try:
            self.sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": {"last_activity": datetime.utcnow()}}
            )
        except Exception as e:
            logger.error(f"❌ Failed to update session activity: {e}")
    
    def invalidate_session(self, session_id: str):
        """Invalidate a session"""
        try:
            self.sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": {"is_active": False}}
            )
            logger.info(f"✅ Session invalidated: {session_id}")
        except Exception as e:
            logger.error(f"❌ Failed to invalidate session: {e}")
    
    def create_user(self, username: str, email: str, role: str = "user") -> Tuple[bool, Optional[str], str]:
        """Create a new user (admin function)"""
        try:
            # Check if username or email already exists
            existing_user = self.users_collection.find_one({
                "$or": [{"username": username}, {"email": email}]
            })
            
            if existing_user:
                return False, None, "Username or email already exists"
            
            # Generate user ID and password
            user_id = f"user_{secrets.token_hex(8)}"
            password = self._generate_password()
            
            # Create user
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                password_hash=self._hash_password(password),
                role=role,
                is_active=True,
                created_at=datetime.utcnow(),
                last_login=None
            )
            
            self._save_user(user)
            logger.info(f"✅ User created: {username}")
            return True, password, f"User {username} created successfully"
        except Exception as e:
            logger.error(f"❌ Failed to create user: {e}")
            return False, None, f"Failed to create user: {str(e)}"
    
    def get_all_users(self) -> List[Dict]:
        """Get all users (admin function)"""
        try:
            users = list(self.users_collection.find({}, {"password_hash": 0}))
            
            # Convert ObjectId to string for JSON serialization
            for user in users:
                if '_id' in user:
                    user['_id'] = str(user['_id'])
                if 'created_at' in user:
                    user['created_at'] = user['created_at'].isoformat()
                if 'last_login' in user and user['last_login']:
                    user['last_login'] = user['last_login'].isoformat()
            
            return users
        except Exception as e:
            logger.error(f"❌ Failed to get users: {e}")
            return []
    
    def get_user_stats(self) -> Dict:
        """Get user statistics (admin function)"""
        try:
            total_users = self.users_collection.count_documents({})
            active_users = self.users_collection.count_documents({"is_active": True})
            admin_users = self.users_collection.count_documents({"role": "admin"})
            today_users = self.users_collection.count_documents({
                "created_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}
            })
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "admin_users": admin_users,
                "today_users": today_users
            }
        except Exception as e:
            logger.error(f"❌ Failed to get user stats: {e}")
            return {}
    
    def update_user_password(self, user_id: str, new_password: str) -> bool:
        """Update user password"""
        try:
            password_hash = self._hash_password(new_password)
            self.users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"password_hash": password_hash}}
            )
            logger.info(f"✅ Password updated for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update password: {e}")
            return False
    
    def update_mocxha_credentials(self, user_id: str, credentials: Dict) -> bool:
        """Update user's Mocxha credentials"""
        try:
            self.users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"mocxha_credentials": credentials}}
            )
            logger.info(f"✅ Mocxha credentials updated for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update Mocxha credentials: {e}")
            return False
    
    def get_mocxha_credentials(self, user_id: str) -> Optional[Dict]:
        """Get user's Mocxha credentials"""
        try:
            user_data = self.users_collection.find_one({"user_id": user_id})
            if user_data and user_data.get("mocxha_credentials"):
                return user_data["mocxha_credentials"]
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get Mocxha credentials: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            user_data = self.users_collection.find_one({"user_id": user_id})
            if not user_data:
                return None
            return self._user_from_dict(user_data)
        except Exception as e:
            logger.error(f"❌ Failed to get user: {e}")
            return None
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user (admin function)"""
        try:
            self.users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"is_active": False}}
            )
            logger.info(f"✅ User deactivated: {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to deactivate user: {e}")
            return False
    
    def activate_user(self, user_id: str) -> bool:
        """Activate a user (admin function)"""
        try:
            self.users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"is_active": True}}
            )
            logger.info(f"✅ User activated: {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to activate user: {e}")
            return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            # Sessions are automatically cleaned up by MongoDB TTL index
            # But we can also manually clean up inactive sessions
            cutoff_time = datetime.utcnow() - timedelta(days=7)
            result = self.sessions_collection.delete_many({
                "last_activity": {"$lt": cutoff_time}
            })
            if result.deleted_count > 0:
                logger.info(f"✅ Cleaned up {result.deleted_count} expired sessions")
        except Exception as e:
            logger.error(f"❌ Failed to cleanup sessions: {e}")
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close() 

    def authenticate_admin(self, username: str, password: str) -> Tuple[bool, Optional[User], str]:
        """Authenticate admin user"""
        try:
            # Find user by username
            user_data = self.users_collection.find_one({"username": username})
            if not user_data:
                return False, None, "Invalid username or password"
            
            user = self._user_from_dict(user_data)
            
            # Check if user is admin
            if user.role != "admin":
                return False, None, "Access denied. Admin privileges required."
            
            # Check if user is active
            if not user.is_active:
                return False, None, "Account is deactivated"
            
            # Verify password
            if not self._verify_password(password, user.password_hash):
                return False, None, "Invalid username or password"
            
            # Update last login
            self.users_collection.update_one(
                {"user_id": user.user_id},
                {"$set": {"last_login": datetime.now()}}
            )
            
            logger.info(f"✅ Admin authentication successful for user: {username}")
            return True, user, "Authentication successful"
            
        except Exception as e:
            logger.error(f"❌ Admin authentication error: {e}")
            return False, None, "Authentication failed"
    
    def create_admin_session(self, admin_user: User, ip_address: str, user_agent: str) -> str:
        """Create admin session"""
        try:
            session_id = secrets.token_urlsafe(32)
            admin_session = UserSession(
                session_id=session_id,
                user_id=admin_user.user_id,
                username=admin_user.username,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                is_active=True,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            session_data = {
                "session_id": session_id,
                "user_id": admin_user.user_id,
                "username": admin_user.username,
                "created_at": admin_session.created_at,
                "last_activity": admin_session.last_activity,
                "is_active": True,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
            
            self.sessions_collection.insert_one(session_data)
            logger.info(f"✅ Admin session created: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create admin session: {e}")
            raise
    
    def get_admin_session(self, session_id: str) -> Optional[UserSession]:
        """Get admin session"""
        try:
            session_data = self.sessions_collection.find_one({"session_id": session_id, "is_active": True})
            if session_data:
                # Check if the session is for an admin user
                user_data = self.users_collection.find_one({"user_id": session_data["user_id"]})
                if user_data and user_data.get("role") == "admin":
                    return UserSession(
                        session_id=session_data["session_id"],
                        user_id=session_data["user_id"],
                        username=session_data["username"],
                        created_at=session_data["created_at"],
                        last_activity=session_data["last_activity"],
                        is_active=session_data["is_active"],
                        ip_address=session_data["ip_address"],
                        user_agent=session_data["user_agent"]
                    )
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get admin session: {e}")
            return None
    
    def update_admin_password(self, username: str, current_password: str, new_password: str) -> Tuple[bool, str]:
        """Update admin password"""
        try:
            # First authenticate the admin
            is_authenticated, user, message = self.authenticate_admin(username, current_password)
            if not is_authenticated:
                return False, message
            
            # Hash the new password
            new_password_hash = self._hash_password(new_password)
            
            # Update the password
            result = self.users_collection.update_one(
                {"user_id": user.user_id},
                {"$set": {"password_hash": new_password_hash}}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Admin password updated for user: {username}")
                return True, "Password updated successfully"
            else:
                return False, "Failed to update password"
                
        except Exception as e:
            logger.error(f"❌ Failed to update admin password: {e}")
            return False, "Failed to update password" 