#!/usr/bin/env python3
"""
Test script for admin authentication functionality
"""

import requests
import json

def test_admin_auth():
    """Test admin authentication functionality"""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Admin Authentication")
    print("=" * 40)
    
    # Step 1: Test admin login with correct credentials
    print("1. Testing admin login with correct credentials...")
    try:
        response = requests.post(f"{base_url}/admin/login", json={
            "username": "Shamlan321",
            "password": "5h4ml4n321"
        })
        
        if response.ok:
            data = response.json()
            admin_session_id = data.get("session_id")
            print(f"✅ Admin login successful, session: {admin_session_id[:20]}...")
            
            # Step 2: Test admin session check
            print("\n2. Testing admin session check...")
            session_response = requests.get(f"{base_url}/admin/check_session", 
                headers={"Authorization": f"Bearer {admin_session_id}"})
            
            if session_response.ok:
                session_data = session_response.json()
                print(f"✅ Admin session check successful: {session_data}")
            else:
                print(f"❌ Admin session check failed: {session_response.text}")
            
            # Step 3: Test admin stats access
            print("\n3. Testing admin stats access...")
            stats_response = requests.get(f"{base_url}/admin/stats", 
                headers={"Authorization": f"Bearer {admin_session_id}"})
            
            if stats_response.ok:
                stats_data = stats_response.json()
                print(f"✅ Admin stats access successful: {stats_data}")
            else:
                print(f"❌ Admin stats access failed: {stats_response.text}")
            
            # Step 4: Test password change
            print("\n4. Testing admin password change...")
            password_response = requests.post(f"{base_url}/admin/change_password", 
                headers={
                    "Authorization": f"Bearer {admin_session_id}",
                    "Content-Type": "application/json"
                },
                json={
                    "current_password": "5h4ml4n321",
                    "new_password": "newpassword123"
                })
            
            if password_response.ok:
                password_data = password_response.json()
                print(f"✅ Admin password change successful: {password_data}")
                
                # Step 5: Test login with new password
                print("\n5. Testing admin login with new password...")
                new_login_response = requests.post(f"{base_url}/admin/login", json={
                    "username": "Shamlan321",
                    "password": "newpassword123"
                })
                
                if new_login_response.ok:
                    print("✅ Admin login with new password successful")
                    
                    # Change password back
                    new_session_id = new_login_response.json().get("session_id")
                    revert_response = requests.post(f"{base_url}/admin/change_password", 
                        headers={
                            "Authorization": f"Bearer {new_session_id}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "current_password": "newpassword123",
                            "new_password": "5h4ml4n321"
                        })
                    
                    if revert_response.ok:
                        print("✅ Password reverted back to original")
                    else:
                        print("⚠️ Failed to revert password")
                else:
                    print(f"❌ Admin login with new password failed: {new_login_response.text}")
            else:
                print(f"❌ Admin password change failed: {password_response.text}")
            
            # Step 6: Test logout
            print("\n6. Testing admin logout...")
            logout_response = requests.post(f"{base_url}/admin/logout", 
                headers={"Authorization": f"Bearer {admin_session_id}"})
            
            if logout_response.ok:
                print("✅ Admin logout successful")
            else:
                print(f"❌ Admin logout failed: {logout_response.text}")
                
        else:
            print(f"❌ Admin login failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Admin authentication test error: {e}")
    
    print("\n🎉 Admin Authentication Test Completed!")

if __name__ == "__main__":
    test_admin_auth() 