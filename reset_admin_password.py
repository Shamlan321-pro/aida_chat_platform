#!/usr/bin/env python3
"""
Script to reset admin password
"""

from pymongo import MongoClient
import hashlib
import os

def reset_admin_password(new_password="admin123"):
    """Reset admin password"""
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    db_name = os.getenv("MONGODB_DB_NAME", "aida_platform")
    
    try:
        client = MongoClient(mongo_uri)
        db = client[db_name]
        
        # Hash the new password
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        
        # Update admin user password
        result = db.users.update_one(
            {"role": "admin"},
            {"$set": {"password_hash": password_hash}}
        )
        
        if result.modified_count > 0:
            print(f"✅ Admin password reset successfully!")
            print(f"   Username: admin")
            print(f"   New Password: {new_password}")
            print(f"\n💡 You can now login with these credentials.")
        else:
            print("❌ Failed to reset admin password")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    reset_admin_password() 