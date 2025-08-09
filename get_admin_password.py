#!/usr/bin/env python3
"""
Script to get the admin password from the database
"""

from pymongo import MongoClient
import os

def get_admin_password():
    """Get admin password from MongoDB"""
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    db_name = os.getenv("MONGODB_DB_NAME", "aida_platform")
    
    try:
        client = MongoClient(mongo_uri)
        db = client[db_name]
        
        # Find admin user
        admin_user = db.users.find_one({"role": "admin"})
        
        if admin_user:
            print(f"✅ Admin user found:")
            print(f"   Username: {admin_user['username']}")
            print(f"   Email: {admin_user['email']}")
            print(f"   Role: {admin_user['role']}")
            print(f"   Active: {admin_user['is_active']}")
            print(f"   Created: {admin_user['created_at']}")
            print(f"   Last Login: {admin_user.get('last_login', 'Never')}")
            
            # Note: We can't retrieve the actual password since it's hashed
            print(f"\n⚠️  Password is hashed and cannot be retrieved.")
            print(f"💡 Check the server logs for the generated password when the admin user was created.")
            print(f"💡 Or create a new admin user with a known password.")
            
        else:
            print("❌ No admin user found in database")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    get_admin_password() 