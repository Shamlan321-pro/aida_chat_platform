import os
import json
import logging
import uuid
import requests
from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables from .env file will not be loaded.")

# --- START: Import AidaERPNextAgent and SessionManager ---
try:
    from services.aida_agent import AidaERPNextAgent, MongoMemoryManager
    from session_manager import SessionManager
    from auth_manager import AuthManager
    # Re-evaluate MONGODB_AVAILABLE based on current environment for the API server
    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
        MONGODB_AVAILABLE = True
    except ImportError:
        MONGODB_AVAILABLE = False
except ImportError as e:
    print(f"Error: Could not import required modules. Details: {e}")
    # Define placeholder classes to avoid immediate crash, though functionality will be broken
    class AidaERPNextAgent:
        def __init__(self, *args, **kwargs):
            raise NotImplementedError("AidaERPNextAgent not imported. Check aida_agent.py.")
        def chat(self, user_input: str):
            return "Error: Agent not initialized due to missing aida_agent.py. Cannot process chat."
    class MongoMemoryManager:
        def __init__(self, *args, **kwargs):
            print("MongoMemoryManager not imported. Using dummy.")
        def store_conversation(self, *args, **kwargs): pass
        def get_recent_context(self, *args, **kwargs): return []
        def get_last_query_result(self, *args, **kwargs): return None
    class SessionManager:
        def __init__(self, *args, **kwargs): pass
        def create_session(self, *args, **kwargs): return str(uuid.uuid4())
        def get_session(self, *args, **kwargs): return None
    class AuthManager:
        def __init__(self, *args, **kwargs): pass
        def authenticate_user(self, *args, **kwargs): return (False, None, "Auth not available")
    MONGODB_AVAILABLE = False
# --- END: Import AidaERPNextAgent and SessionManager ---


# Configure logging for the Flask app
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
flask_logger = logging.getLogger('flask_server')
flask_logger.setLevel(logging.INFO)

app = Flask(__name__)
CORS(app, origins="*")  # Allow all origins
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey_aida_erpnext_agent") # IMPORTANT: Change this in production!

# Initialize session manager for persistent sessions with MongoDB
mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
db_name = os.getenv("MONGODB_DB_NAME", "aida_platform")
session_manager = SessionManager(mongo_uri=mongo_uri, db_name=db_name)

# Initialize authentication manager
auth_manager = AuthManager(mongo_uri=mongo_uri, db_name=db_name)

# In-memory store for active AidaERPNextAgent instances, keyed by session_id
# Sessions are now persistent, but agents are still created on-demand
active_agents: Dict[str, AidaERPNextAgent] = {}

# Clear all sessions on server restart to ensure fresh state
session_manager.clear_all_sessions()
flask_logger.info("All sessions cleared on server restart")


@app.route('/init_session', methods=['POST'])
def init_session():
    """
    Initialize or restore a persistent session with credential storage.
    Supports both new sessions and existing session restoration.
    """
    data = request.get_json()
    
    # Get request information for logging and session management
    origin = request.headers.get('Origin', '')
    user_agent = request.headers.get('User-Agent', '')
    ip_address = request.remote_addr
    
    flask_logger.info(f"Init session request from: {ip_address}, Origin: {origin}")
    
    erpnext_url = data.get('mocxha_url') or data.get('erpnext_url')  # Support both new and legacy field names
    username = data.get('username')
    password = data.get('password')
    google_api_key = os.getenv('GOOGLE_API_KEY')
    site_base_url = data.get('site_base_url', erpnext_url)
    restore_session = data.get('restore_session', True)  # Default to trying to restore

    # Security: Don't log sensitive data
    flask_logger.info(f"Session request - URL: {erpnext_url}, Username: {username}, Restore: {restore_session}")

    # Validate required fields
    missing_fields = []
    if not erpnext_url:
        missing_fields.append("mocxha_url")
    if not username:
        missing_fields.append("username")
    
    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        flask_logger.error(error_msg)
        return jsonify({"error": error_msg}), 400
    
    # Validate Google API key from environment
    if not google_api_key:
        error_msg = "Google API key not configured on server. Please check environment variables."
        flask_logger.error(error_msg)
        return jsonify({"error": error_msg}), 500

    # Enhanced session token validation for security
    if password == "session_token":
        api_key = data.get('api_key')  # This will be the user email
        api_secret = data.get('api_secret')  # This will be the session ID
        
        if not all([api_key, api_secret]):
            return jsonify({"error": "API key and secret required for session token authentication."}), 400
        
        # Validate the Frappe session
        try:
            session_validation_url = f"{erpnext_url}/api/method/frappe.auth.get_logged_user"
            headers = {
                'Cookie': f'sid={api_secret}',
                'Content-Type': 'application/json',
                'User-Agent': 'AIDA-API-Server'
            }
            
            response = requests.get(session_validation_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                if user_data.get('message') == api_key:
                    flask_logger.info(f"Session validated for user: {api_key}")
                    username = api_key
                    password = api_secret
                else:
                    flask_logger.warning(f"Session validation failed for user: {api_key}")
                    return jsonify({"error": "Session validation failed. Invalid user."}), 401
            else:
                flask_logger.warning(f"Session validation returned status: {response.status_code}")
                return jsonify({"error": "Session validation failed. Please log in again."}), 401
                
        except Exception as e:
            flask_logger.error(f"Session validation error: {e}")
            return jsonify({"error": "Could not validate session. Please try again."}), 500
    
    # Security: Validate Google API key format from environment
    if len(google_api_key) < 20:
        return jsonify({"error": "Invalid Google API Key format in server configuration."}), 500
    
    try:
        # Try to find existing session if restore is enabled
        existing_session_id = None
        if restore_session:
            existing_session_id = session_manager.find_existing_session(
                user_agent, ip_address, erpnext_url, username
            )
            
            if existing_session_id:
                # Verify credentials match
                if session_manager.verify_credentials(existing_session_id, password, google_api_key):
                    # Update access time and restore session
                    session_manager.update_session_access(existing_session_id)
                    
                    # Create agent if not already active
                    if existing_session_id not in active_agents:
                        session_data = session_manager.get_session(existing_session_id)
                        agent = AidaERPNextAgent(
                            erpnext_url=session_data.erpnext_url,
                            username=session_data.username,
                            password=password,  # Use actual password, not hash
                            google_api_key=google_api_key,  # Use actual key, not hash
                            mongo_uri=None,  # Using SQLite now
                            session_id=existing_session_id,
                            site_base_url=session_data.site_base_url
                        )
                        active_agents[existing_session_id] = agent
                    
                    flask_logger.info(f"Restored session {existing_session_id} for user: {username}")
                    return jsonify({
                        "session_id": existing_session_id, 
                        "message": "Session restored successfully.",
                        "restored": True
                    }), 200
                else:
                    flask_logger.info(f"Credentials changed for user {username}, creating new session")
        
        # Create new session
        session_id = session_manager.create_session(
            erpnext_url=erpnext_url,
            username=username,
            password=password,
            google_api_key=google_api_key,
            user_agent=user_agent,
            ip_address=ip_address,
            site_base_url=site_base_url
        )
        
        # Create and store agent instance
        agent = AidaERPNextAgent(
            erpnext_url=erpnext_url,
            username=username,
            password=password,
            google_api_key=google_api_key,
            mongo_uri=None,  # Using SQLite now
            session_id=session_id,
            site_base_url=site_base_url
        )
        active_agents[session_id] = agent
        
        flask_logger.info(f"New session {session_id} created for user: {username}")
        return jsonify({
            "session_id": session_id, 
            "message": "New session created successfully.",
            "restored": False
        }), 200
        
    except Exception as e:
        flask_logger.error(f"Failed to initialize session: {e}", exc_info=True)
        error_msg = "Failed to initialize session. Please check your credentials."
        return jsonify({"error": error_msg}), 500

@app.route('/create_leads', methods=['POST'])
def create_leads():
    """
    Create leads using Google Maps business search - separated from main agent.
    """
    data = request.get_json()
    
    # Extract parameters
    erpnext_url = data.get('mocxha_url') or data.get('erpnext_url')  # Support both new and legacy field names
    username = data.get('username')
    password = data.get('password')
    google_api_key = data.get('google_api_key')
    business_type = data.get('business_type')
    location = data.get('location')
    count = data.get('count', 10)
    
    # Validate required fields
    missing_fields = []
    if not erpnext_url:
        missing_fields.append("mocxha_url")
    if not username:
        missing_fields.append("username")
    if not password:
        missing_fields.append("password")
    if not google_api_key:
        missing_fields.append("google_api_key")
    if not business_type:
        missing_fields.append("business_type")
    if not location:
        missing_fields.append("location")
    
    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        flask_logger.error(error_msg)
        return jsonify({"error": error_msg}), 400
    
    # Security: Rate limiting check (basic)
    client_ip = request.remote_addr
    current_time = datetime.now()
    
    if not hasattr(app, 'lead_rate_limits'):
        app.lead_rate_limits = {}
    
    if client_ip in app.lead_rate_limits:
        last_requests = app.lead_rate_limits[client_ip]
        recent_requests = [t for t in last_requests if (current_time - t).seconds < 300]  # 5 minutes
        if len(recent_requests) >= 5:  # Max 5 lead creation requests per 5 minutes
            flask_logger.warning(f"Lead creation rate limit exceeded for IP: {client_ip}")
            return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429
        app.lead_rate_limits[client_ip] = recent_requests + [current_time]
    else:
        app.lead_rate_limits[client_ip] = [current_time]
    
    try:
        # Create a temporary agent instance for lead creation
        temp_session_id = str(uuid.uuid4())
        agent = AidaERPNextAgent(
            erpnext_url=erpnext_url,
            username=username,
            password=password,
            google_api_key=google_api_key,
            mongo_uri=None,  # No persistent memory needed for lead creation
            session_id=temp_session_id
        )
        
        # Use the lead creation functionality
        if not agent.lead_creation_agent:
            return jsonify({"error": "Lead creation not available. Google Maps API key required."}), 400
        
        result = agent.lead_creation_agent.create_leads(
            business_type=business_type,
            location=location,
            count=count
        )
        
        flask_logger.info(f"Lead creation completed - Type: {business_type}, Location: {location}, Count: {count}")
        return jsonify({"success": True, "result": result}), 200
        
    except Exception as e:
        flask_logger.error(f"Lead creation failed: {e}", exc_info=True)
        return jsonify({"error": f"Lead creation failed: {str(e)}"}), 500

@app.route('/chat', methods=['POST'])
def chat_with_agent():
    """
    Send a message to the AidaERPNextAgent for a given session with persistent history.
    """
    data = request.get_json()
    session_id = data.get('session_id')
    user_input = data.get('user_input')

    # Security: Rate limiting check (basic)
    client_ip = request.remote_addr
    current_time = datetime.now()
    
    # Basic rate limiting: max 10 requests per minute per IP
    if not hasattr(app, 'rate_limits'):
        app.rate_limits = {}
    
    if client_ip in app.rate_limits:
        last_requests = app.rate_limits[client_ip]
        recent_requests = [t for t in last_requests if (current_time - t).seconds < 60]
        if len(recent_requests) >= 10:
            flask_logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429
        app.rate_limits[client_ip] = recent_requests + [current_time]
    else:
        app.rate_limits[client_ip] = [current_time]

    if not session_id or not user_input:
        return jsonify({"error": "Session ID and user input are required."}), 400

    # Security: Sanitize user input
    user_input = user_input.strip()
    if len(user_input) > 2000:  # Limit message length
        return jsonify({"error": "Message too long. Please limit to 2000 characters."}), 400

    # Verify session exists in session manager
    session_data = session_manager.get_session(session_id)
    if not session_data:
        return jsonify({"error": "Invalid or expired session. Please reconnect."}), 404
    
    # Update session access time
    session_manager.update_session_access(session_id)

    # Get or create agent instance
    agent = active_agents.get(session_id)
    if not agent:
        # Session exists but agent not in memory - recreate it
        # This can happen with multiple Gunicorn workers or after server restart
        # Since we only store hashed credentials, we cannot recreate the agent
        # The user needs to reconnect to provide the actual credentials again
        flask_logger.warning(f"Agent not found for session {session_id}. User needs to reconnect.")
        return jsonify({
            "error": "Session found but agent not active. Please reconnect to restore your session.",
            "reconnect_required": True
        }), 410

    try:
        # Get chat response from agent
        response = agent.chat(user_input)
        
        # Store in session manager's chat history (in addition to agent's memory)
        # This provides redundant storage and better persistence
        session_manager.store_chat_message(
            session_id=session_id,
            user_message=user_input,
            ai_response=response
        )
        
        flask_logger.info(f"Chat - Session: {session_id}, User message length: {len(user_input)}")
        return jsonify({"session_id": session_id, "response": response}), 200
        
    except Exception as e:
        flask_logger.error(f"Chat error for session {session_id}: {e}", exc_info=True)
        error_response = "An error occurred. Please try again."
        
        # Store error in chat history too
        session_manager.store_chat_message(
            session_id=session_id,
            user_message=user_input,
            ai_response=error_response
        )
        
        return jsonify({"error": error_response}), 500

@app.route('/get_chat_history/<session_id>', methods=['GET'])
def get_chat_history(session_id):
    """
    Retrieve chat history for a session.
    """
    if not session_id:
        return jsonify({"error": "Session ID is required."}), 400
    
    # Verify session exists
    session_data = session_manager.get_session(session_id)
    if not session_data:
        return jsonify({"error": "Invalid session."}), 404
    
    try:
        # Get chat history from session manager
        limit = request.args.get('limit', 20, type=int)
        history = session_manager.get_chat_history(session_id, limit=limit)
        
        # Format history for frontend
        formatted_history = []
        i = 0
        while i < len(history):
            msg = history[i]
            if msg["role"] == "user":
                user_message = msg["content"]
                ai_response = ""
                
                # Look for the corresponding AI response
                if i + 1 < len(history) and history[i + 1]["role"] == "assistant":
                    ai_response = history[i + 1]["content"]
                    i += 1  # Skip the AI message in next iteration
                
                formatted_history.append({
                    "timestamp": msg["timestamp"],
                    "user_message": user_message,
                    "ai_response": ai_response
                })
            i += 1
        
        return jsonify({
            "session_id": session_id,
            "history": formatted_history,
            "count": len(formatted_history)
        }), 200
        
    except Exception as e:
        flask_logger.error(f"Error retrieving chat history for session {session_id}: {e}")
        return jsonify({"error": "Failed to retrieve chat history."}), 500

@app.route('/clear_session', methods=['POST'])
def clear_session():
    """
    Clear a specific session and remove its agent instance.
    """
    data = request.get_json()
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({"error": "Session ID is required."}), 400

    # Remove from active agents
    if session_id in active_agents:
        del active_agents[session_id]
        flask_logger.info(f"Active agent for session {session_id} cleared.")
    
    # Note: We don't delete the session from session_manager to preserve history
    # The session will naturally expire based on the cleanup policy
    
    return jsonify({"message": f"Session {session_id} cleared successfully."}), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        "status": "healthy",
        "active_sessions": len(active_agents),
        "mongodb_available": MONGODB_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/session_status/<session_id>', methods=['GET'])
def session_status(session_id):
    """Check if a session is still active"""
    try:
        session = session_manager.get_session(session_id)
        if session:
            # Update last access time
            session_manager.update_session_access(session_id)
            return jsonify({
                "active": True, 
                "session_id": session_id,
                "user_identifier": session.user_identifier
            })
        else:
            return jsonify({"active": False}), 404
    except Exception as e:
        flask_logger.error(f"Error checking session status: {str(e)}")
        return jsonify({"error": "Failed to check session status"}), 500

@app.route('/get_recent_chats', methods=['GET'])
def get_recent_chats():
    """Get recent chats for the current user"""
    try:
        # Check authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401
        
        session_id = auth_header.split(' ')[1]
        
        # Get user session
        session = auth_manager.get_session(session_id)
        if not session or not session.is_active:
            return jsonify({"error": "Invalid session"}), 401
        
        # Get chats using user_id
        chats = session_manager.get_recent_chats(user_id=session.user_id, limit=20)
        return jsonify({"chats": chats}), 200
    except Exception as e:
        flask_logger.error(f"Error getting recent chats: {str(e)}")
        return jsonify({"error": "Failed to get recent chats"}), 500

@app.route('/get_chat/<chat_id>', methods=['GET'])
def get_chat(chat_id):
    """Get a specific chat by ID"""
    try:
        # Check authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401
        
        session_id = auth_header.split(' ')[1]
        
        # Get user session
        session = auth_manager.get_session(session_id)
        if not session or not session.is_active:
            return jsonify({"error": "Invalid session"}), 401
        
        chat = session_manager.get_chat_by_id(chat_id, user_id=session.user_id)
        if chat:
            return jsonify({"chat": chat}), 200
        else:
            return jsonify({"error": "Chat not found"}), 404
    except Exception as e:
        flask_logger.error(f"Error getting chat: {str(e)}")
        return jsonify({"error": "Failed to get chat"}), 500

@app.route('/save_chat', methods=['POST'])
def save_chat():
    """Save a new chat"""
    try:
        # Check authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401
        
        session_id = auth_header.split(' ')[1]
        
        # Get user session
        session = auth_manager.get_session(session_id)
        if not session or not session.is_active:
            return jsonify({"error": "Invalid session"}), 401
        
        data = request.get_json()
        mocxha_session_id = data.get('session_id')
        title = data.get('title', 'New Chat')
        preview = data.get('preview', '')
        messages = data.get('messages', [])
        
        if not mocxha_session_id:
            return jsonify({"error": "Session ID required"}), 400
        
        chat_id = session_manager.save_chat(mocxha_session_id, title, preview, messages)
        return jsonify({"chat_id": chat_id, "message": "Chat saved successfully"}), 200
    except Exception as e:
        flask_logger.error(f"Error saving chat: {str(e)}")
        return jsonify({"error": "Failed to save chat"}), 500

@app.route('/delete_chat/<chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    """Delete a chat"""
    try:
        # Check authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401
        
        session_id = auth_header.split(' ')[1]
        
        # Get user session
        session = auth_manager.get_session(session_id)
        if not session or not session.is_active:
            return jsonify({"error": "Invalid session"}), 401
        
        success = session_manager.delete_chat(chat_id, user_id=session.user_id)
        if success:
            return jsonify({"message": "Chat deleted successfully"}), 200
        else:
            return jsonify({"error": "Chat not found"}), 404
    except Exception as e:
        flask_logger.error(f"Error deleting chat: {str(e)}")
        return jsonify({"error": "Failed to delete chat"}), 500

# Authentication endpoints
@app.route('/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    
    try:
        success, user, message = auth_manager.authenticate_user(username, password)
        
        if success:
            # Create user session
            session_id = auth_manager.create_user_session(
                user, 
                request.remote_addr, 
                request.headers.get('User-Agent', '')
            )
            
            return jsonify({
                "success": True,
                "message": message,
                "session_id": session_id,
                "user_id": user.user_id,
                "username": user.username,
                "role": user.role
            })
        else:
            return jsonify({"error": message}), 401
    except Exception as e:
        flask_logger.error(f"Login error: {e}")
        return jsonify({"error": "Authentication failed"}), 500

@app.route('/auth/check_session', methods=['GET'])
def check_session():
    """Check if user session is valid"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "No valid session token"}), 401
    
    session_id = auth_header.split(' ')[1]
    
    try:
        session = auth_manager.get_session(session_id)
        if session and session.is_active:
            # Update session activity
            auth_manager.update_session_activity(session_id)
            return jsonify({
                "valid": True,
                "user_id": session.user_id,
                "username": session.username
            })
        else:
            return jsonify({"error": "Invalid or expired session"}), 401
    except Exception as e:
        flask_logger.error(f"Session check error: {e}")
        return jsonify({"error": "Session validation failed"}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "No valid session token"}), 401
    
    session_id = auth_header.split(' ')[1]
    
    try:
        auth_manager.invalidate_session(session_id)
        return jsonify({"success": True, "message": "Logged out successfully"})
    except Exception as e:
        flask_logger.error(f"Logout error: {e}")
        return jsonify({"error": "Logout failed"}), 500

@app.route('/auth/change_password', methods=['POST'])
def change_password():
    """User password change endpoint"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "No valid session token"}), 401
    
    session_id = auth_header.split(' ')[1]
    
    try:
        # Get user session
        session = auth_manager.get_session(session_id)
        if not session or not session.is_active:
            return jsonify({"error": "Invalid session"}), 401
        
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({"error": "Current password and new password are required"}), 400
        
        # Get user by ID
        user = auth_manager.get_user_by_id(session.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Verify current password
        if not auth_manager._verify_password(current_password, user.password_hash):
            return jsonify({"error": "Current password is incorrect"}), 401
        
        # Update password
        success = auth_manager.update_user_password(session.user_id, new_password)
        if success:
            return jsonify({"success": True, "message": "Password changed successfully"})
        else:
            return jsonify({"error": "Failed to change password"}), 500
            
    except Exception as e:
        flask_logger.error(f"Change password error: {e}")
        return jsonify({"error": "Password change failed"}), 500

@app.route('/user/connect_mocxha', methods=['POST'])
def user_connect_mocxha():
    """
    Connect to Mocxha for authenticated users and save credentials.
    """
    # Check authentication
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authentication required"}), 401
    
    session_id = auth_header.split(' ')[1]
    
    try:
        # Get user session
        session = auth_manager.get_session(session_id)
        if not session or not session.is_active:
            return jsonify({"error": "Invalid session"}), 401
        
        data = request.get_json()
        erpnext_url = data.get('mocxha_url') or data.get('erpnext_url')
        username = data.get('username')
        password = data.get('password')
        site_base_url = data.get('site_base_url', erpnext_url)
        
        # Validate required fields
        if not all([erpnext_url, username, password]):
            return jsonify({"error": "Missing required fields: mocxha_url, username, password"}), 400
        
        # Validate Google API key
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key:
            return jsonify({"error": "Google API key not configured"}), 500
        
        # Test the connection
        try:
            # Create a temporary agent to test the connection
            test_agent = AidaERPNextAgent(
                erpnext_url=erpnext_url,
                username=username,
                password=password,
                google_api_key=google_api_key,
                mongo_uri=None,
                session_id="test",
                site_base_url=site_base_url
            )
            
            # Test the connection by trying to get user info
            test_response = test_agent.chat("Hello")
            if not test_response:
                return jsonify({"error": "Failed to connect to Mocxha. Please check your credentials."}), 400
            
        except Exception as e:
            flask_logger.error(f"Mocxha connection test failed: {e}")
            return jsonify({"error": f"Failed to connect to Mocxha: {str(e)}"}), 400
        
        # Save credentials to user account
        credentials = {
            "mocxha_url": erpnext_url,
            "username": username,
            "password": password,  # Note: This should be encrypted in production
            "site_base_url": site_base_url,
            "saved_at": datetime.utcnow().isoformat()
        }
        
        success = auth_manager.update_mocxha_credentials(session.user_id, credentials)
        if not success:
            return jsonify({"error": "Failed to save credentials"}), 500
        
        # Create session for this connection
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.remote_addr
        
        mocxha_session_id = session_manager.create_session(
            erpnext_url=erpnext_url,
            username=username,
            password=password,
            google_api_key=google_api_key,
            user_agent=user_agent,
            ip_address=ip_address,
            site_base_url=site_base_url,
            user_id=session.user_id
        )
        
        # Create agent
        active_agents[mocxha_session_id] = AidaERPNextAgent(
            erpnext_url=erpnext_url,
            username=username,
            password=password,
            google_api_key=google_api_key,
            mongo_uri=None,
            session_id=mocxha_session_id,
            site_base_url=site_base_url
        )
        
        flask_logger.info(f"✅ Mocxha connected for user {session.username}: {mocxha_session_id}")
        return jsonify({
            "session_id": mocxha_session_id,
            "message": "Mocxha connected successfully",
            "credentials_saved": True
        })
        
    except Exception as e:
        flask_logger.error(f"User Mocxha connection error: {e}")
        return jsonify({"error": f"Failed to connect to Mocxha: {str(e)}"}), 500

@app.route('/user/auto_connect_mocxha', methods=['POST'])
def user_auto_connect_mocxha():
    """
    Auto-connect to Mocxha using saved credentials for authenticated users.
    """
    # Check authentication
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authentication required"}), 401
    
    session_id = auth_header.split(' ')[1]
    
    try:
        # Get user session
        session = auth_manager.get_session(session_id)
        if not session or not session.is_active:
            return jsonify({"error": "Invalid session"}), 401
        
        # Get user's saved Mocxha credentials
        credentials = auth_manager.get_mocxha_credentials(session.user_id)
        if not credentials:
            return jsonify({"error": "No saved Mocxha credentials found"}), 404
        
        # Validate Google API key
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key:
            return jsonify({"error": "Google API key not configured"}), 500
        
        # Test the connection with saved credentials
        try:
            # Create a temporary agent to test the connection
            test_agent = AidaERPNextAgent(
                erpnext_url=credentials["mocxha_url"],
                username=credentials["username"],
                password=credentials["password"],
                google_api_key=google_api_key,
                mongo_uri=None,
                session_id="test",
                site_base_url=credentials.get("site_base_url", credentials["mocxha_url"])
            )
            
            # Test the connection by trying to get user info
            test_response = test_agent.chat("Hello")
            if not test_response:
                return jsonify({"error": "Failed to connect to Mocxha with saved credentials. Please reconnect."}), 400
            
        except Exception as e:
            flask_logger.error(f"Mocxha auto-connection test failed: {e}")
            return jsonify({"error": f"Failed to connect to Mocxha: {str(e)}"}), 400
        
        # Check for existing session first
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.remote_addr
        
        # Try to find existing session
        existing_session_id = session_manager.find_existing_session(
            user_agent=user_agent,
            ip_address=ip_address,
            erpnext_url=credentials["mocxha_url"],
            username=credentials["username"],
            user_id=session.user_id
        )
        
        if existing_session_id:
            # Use existing session
            existing_session = session_manager.get_session(existing_session_id)
            if existing_session and existing_session.is_active:
                # Update session access time
                session_manager.update_session_access(existing_session_id)
                
                # Check if agent already exists
                if existing_session_id not in active_agents:
                    # Create agent for existing session
                    active_agents[existing_session_id] = AidaERPNextAgent(
                        erpnext_url=credentials["mocxha_url"],
                        username=credentials["username"],
                        password=credentials["password"],
                        google_api_key=google_api_key,
                        mongo_uri=None,
                        session_id=existing_session_id,
                        site_base_url=credentials.get("site_base_url", credentials["mocxha_url"])
                    )
                
                flask_logger.info(f"✅ Mocxha auto-connected using existing session for user {session.username}: {existing_session_id}")
                return jsonify({
                    "session_id": existing_session_id,
                    "message": "Mocxha auto-connected using existing session"
                })
        
        # Create new session if no existing session found
        mocxha_session_id = session_manager.create_session(
            erpnext_url=credentials["mocxha_url"],
            username=credentials["username"],
            password=credentials["password"],
            google_api_key=google_api_key,
            user_agent=user_agent,
            ip_address=ip_address,
            site_base_url=credentials.get("site_base_url", credentials["mocxha_url"]),
            user_id=session.user_id
        )
        
        # Create agent
        active_agents[mocxha_session_id] = AidaERPNextAgent(
            erpnext_url=credentials["mocxha_url"],
            username=credentials["username"],
            password=credentials["password"],
            google_api_key=google_api_key,
            mongo_uri=None,
            session_id=mocxha_session_id,
            site_base_url=credentials.get("site_base_url", credentials["mocxha_url"])
        )
        
        flask_logger.info(f"✅ Mocxha auto-connected with new session for user {session.username}: {mocxha_session_id}")
        return jsonify({
            "session_id": mocxha_session_id,
            "message": "Mocxha connected successfully with saved credentials",
            "credentials_saved": True
        })
        
    except Exception as e:
        flask_logger.error(f"User Mocxha auto-connection error: {e}")
        return jsonify({"error": f"Failed to connect to Mocxha: {str(e)}"}), 500

@app.route('/user/mocxha_credentials', methods=['GET'])
def get_user_mocxha_credentials():
    """
    Get user's saved Mocxha credentials.
    """
    # Check authentication
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authentication required"}), 401
    
    session_id = auth_header.split(' ')[1]
    
    try:
        # Get user session
        session = auth_manager.get_session(session_id)
        if not session or not session.is_active:
            return jsonify({"error": "Invalid session"}), 401
        
        # Get user's Mocxha credentials
        credentials = auth_manager.get_mocxha_credentials(session.user_id)
        
        if credentials:
            # Don't return the actual password for security
            safe_credentials = {
                "mocxha_url": credentials.get("mocxha_url"),
                "username": credentials.get("username"),
                "site_base_url": credentials.get("site_base_url"),
                "saved_at": credentials.get("saved_at"),
                "has_credentials": True
            }
            return jsonify(safe_credentials)
        else:
            return jsonify({"has_credentials": False})
            
    except Exception as e:
        flask_logger.error(f"Get Mocxha credentials error: {e}")
        return jsonify({"error": "Failed to get credentials"}), 500

# Admin authentication endpoints
@app.route('/admin/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400
        
        # Authenticate admin
        is_authenticated, admin_user, message = auth_manager.authenticate_admin(username, password)
        
        if is_authenticated and admin_user:
            # Create admin session
            session_id = auth_manager.create_admin_session(
                admin_user=admin_user,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            
            flask_logger.info(f"Admin login successful: {username}")
            return jsonify({
                "success": True,
                "session_id": session_id,
                "message": "Admin login successful",
                "user": {
                    "username": admin_user.username,
                    "role": admin_user.role
                }
            }), 200
        else:
            flask_logger.warning(f"Admin login failed: {username} - {message}")
            return jsonify({"error": message}), 401
            
    except Exception as e:
        flask_logger.error(f"Admin login error: {e}")
        return jsonify({"error": "Login failed"}), 500

@app.route('/admin/check_session', methods=['GET'])
def admin_check_session():
    """Check admin session validity"""
    try:
        session_id = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not session_id:
            return jsonify({"error": "No session provided"}), 401
        
        admin_session = auth_manager.get_admin_session(session_id)
        if not admin_session:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        # Update session activity
        auth_manager.update_session_activity(session_id)
        
        return jsonify({
            "valid": True,
            "user": {
                "username": admin_session.username,
                "role": "admin"
            }
        }), 200
        
    except Exception as e:
        flask_logger.error(f"Admin session check error: {e}")
        return jsonify({"error": "Session check failed"}), 500

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    """Admin logout endpoint"""
    try:
        session_id = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if session_id:
            auth_manager.invalidate_session(session_id)
            flask_logger.info("Admin logout successful")
        
        return jsonify({"success": True, "message": "Logout successful"}), 200
        
    except Exception as e:
        flask_logger.error(f"Admin logout error: {e}")
        return jsonify({"error": "Logout failed"}), 500

@app.route('/admin/change_password', methods=['POST'])
def admin_change_password():
    """Change admin password"""
    try:
        session_id = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not session_id:
            return jsonify({"error": "No session provided"}), 401
        
        admin_session = auth_manager.get_admin_session(session_id)
        if not admin_session:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({"error": "Current password and new password are required"}), 400
        
        # Update admin password
        success, message = auth_manager.update_admin_password(
            admin_session.username, current_password, new_password
        )
        
        if success:
            flask_logger.info(f"Admin password changed for user: {admin_session.username}")
            return jsonify({"success": True, "message": message}), 200
        else:
            return jsonify({"error": message}), 400
            
    except Exception as e:
        flask_logger.error(f"Admin password change error: {e}")
        return jsonify({"error": "Password change failed"}), 500

@app.route('/admin/stats', methods=['GET'])
def admin_stats():
    """Get platform statistics (admin only)"""
    try:
        # Check admin authentication
        session_id = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not session_id:
            return jsonify({"error": "No session provided"}), 401
        
        admin_session = auth_manager.get_admin_session(session_id)
        if not admin_session:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        # Update session activity
        auth_manager.update_session_activity(session_id)
        
        stats = auth_manager.get_user_stats()
        return jsonify({"success": True, "stats": stats}), 200
    except Exception as e:
        flask_logger.error(f"Admin stats error: {e}")
        return jsonify({"error": "Failed to get stats"}), 500

@app.route('/admin/users', methods=['GET'])
def admin_users():
    """Get all users (admin only)"""
    try:
        # Check admin authentication
        session_id = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not session_id:
            return jsonify({"error": "No session provided"}), 401
        
        admin_session = auth_manager.get_admin_session(session_id)
        if not admin_session:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        # Update session activity
        auth_manager.update_session_activity(session_id)
        
        users = auth_manager.get_all_users()
        return jsonify({"success": True, "users": users}), 200
    except Exception as e:
        flask_logger.error(f"Admin users error: {e}")
        return jsonify({"error": "Failed to get users"}), 500

@app.route('/admin/create_user', methods=['POST'])
def admin_create_user():
    """Create a new user (admin only)"""
    try:
        # Check admin authentication
        session_id = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not session_id:
            return jsonify({"error": "No session provided"}), 401
        
        admin_session = auth_manager.get_admin_session(session_id)
        if not admin_session:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        # Update session activity
        auth_manager.update_session_activity(session_id)
        
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        role = data.get('role', 'user')
        
        if not username or not email:
            return jsonify({"error": "Username and email are required"}), 400
        
        success, user_id, message = auth_manager.create_user(username, email, role)
        
        if success:
            return jsonify({"success": True, "user_id": user_id, "message": message}), 201
        else:
            return jsonify({"error": message}), 400
    except Exception as e:
        flask_logger.error(f"Create user error: {e}")
        return jsonify({"error": "Failed to create user"}), 500

@app.route('/admin/deactivate_user/<user_id>', methods=['POST'])
def admin_deactivate_user(user_id):
    """Deactivate a user (admin only)"""
    try:
        # Check admin authentication
        session_id = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not session_id:
            return jsonify({"error": "No session provided"}), 401
        
        admin_session = auth_manager.get_admin_session(session_id)
        if not admin_session:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        # Update session activity
        auth_manager.update_session_activity(session_id)
        
        success = auth_manager.deactivate_user(user_id)
        if success:
            return jsonify({"success": True, "message": "User deactivated successfully"})
        else:
            return jsonify({"error": "Failed to deactivate user"}), 500
    except Exception as e:
        flask_logger.error(f"Deactivate user error: {e}")
        return jsonify({"error": "Failed to deactivate user"}), 500

@app.route('/admin/activate_user/<user_id>', methods=['POST'])
def admin_activate_user(user_id):
    """Activate a user (admin only)"""
    try:
        # Check admin authentication
        session_id = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not session_id:
            return jsonify({"error": "No session provided"}), 401
        
        admin_session = auth_manager.get_admin_session(session_id)
        if not admin_session:
            return jsonify({"error": "Invalid or expired session"}), 401
        
        # Update session activity
        auth_manager.update_session_activity(session_id)
        
        success = auth_manager.activate_user(user_id)
        if success:
            return jsonify({"success": True, "message": "User activated successfully"})
        else:
            return jsonify({"error": "Failed to activate user"}), 500
    except Exception as e:
        flask_logger.error(f"Activate user error: {e}")
        return jsonify({"error": "Failed to activate user"}), 500

# Serve static files
@app.route('/login')
def login_page():
    """Serve login page"""
    return send_from_directory('web_ui', 'login.html')

@app.route('/admin-login')
def admin_login_page():
    """Serve admin login page"""
    return send_from_directory('web_ui', 'admin_login.html')

@app.route('/admin')
def admin_page():
    """Serve admin panel (protected)"""
    return send_from_directory('web_ui', 'admin.html')

@app.route('/admin.js')
def serve_admin_js():
    """Serve admin JavaScript"""
    return send_from_directory('web_ui', 'admin.js')

@app.route('/admin_login.js')
def serve_admin_login_js():
    """Serve admin login JavaScript"""
    return send_from_directory('web_ui', 'admin_login.js')

@app.route('/login.js')
def serve_login_js():
    """Serve login JavaScript"""
    return send_from_directory('web_ui', 'login.js')

@app.route('/')
def index():
    """Serve the main web UI"""
    return send_from_directory('web_ui', 'index.html')

@app.route('/web_ui/<path:filename>')
def serve_static(filename):
    """Serve static files from web_ui directory"""
    return send_from_directory('web_ui', filename)

@app.route('/styles.css')
def serve_styles():
    """Serve styles.css directly"""
    return send_from_directory('web_ui', 'styles.css')

@app.route('/script.js')
def serve_script():
    """Serve script.js directly"""
    return send_from_directory('web_ui', 'script.js')

@app.route('/api')
def api_info():
    """API information endpoint"""
    return jsonify({"message": "Aida ERPNext AI Agent API is running. Use /init_session to start and /chat to interact."})

# Add CORS headers for better integration
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

if __name__ == '__main__':
    # Ensure Flask secret key is set for session management
    if not os.getenv("FLASK_SECRET_KEY"):
        flask_logger.warning("FLASK_SECRET_KEY not set. Using a default for development. Set a strong secret key in production!")

    # Set default values for environment variables if not already set, for local testing.
    # In production, these should be securely managed.
    os.environ.setdefault("ERPNEXT_URL", "http://localhost:8000")
    os.environ.setdefault("ERPNEXT_USERNAME", "Administrator")
    os.environ.setdefault("ERPNEXT_PASSWORD", "admin")
    os.environ.setdefault("GOOGLE_API_KEY", "YOUR_GOOGLE_API_KEY_HERE") # Replace with your actual key

    # Check if we're running in production mode
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    if debug_mode:
        flask_logger.info("Starting Aida ERPNext AI Agent API server in DEBUG mode...")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        flask_logger.info("Starting Aida ERPNext AI Agent API server in PRODUCTION mode...")
        app.run(debug=False, host='0.0.0.0', port=5000)