#!/usr/bin/env python3
"""
Debug script for login issues
Run this to test your login functionality step by step
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = "http://localhost:5000"  # Change this to your Flask app URL
TEST_EMAIL = "test@example.com"  # Change this to a test user email
TEST_PASSWORD = "testpassword123"  # Change this to a test user password

def test_session_debug():
    """Test the session debug endpoint"""
    print("🔍 Testing session debug endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/session-debug")
        if response.status_code == 200:
            data = response.json()
            print("✅ Session debug info:")
            for key, value in data.items():
                print(f"   {key}: {value}")
            return True
        else:
            print(f"❌ Session debug failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Session debug error: {e}")
        return False

def test_auth_status():
    """Test the authentication status endpoint"""
    print("\n🔍 Testing authentication status...")
    try:
        response = requests.get(f"{BASE_URL}/test-auth")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Auth status: {data['status']}")
            if data['status'] == 'authenticated':
                print(f"   User: {data['email']}")
                print(f"   Paid: {data['is_paid']}")
                print(f"   Remaining analyses: {data['remaining_analyses']}")
            return data['status']
        else:
            print(f"❌ Auth status failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Auth status error: {e}")
        return None

def test_login():
    """Test user login"""
    print("\n🔍 Testing user login...")
    try:
        login_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "remember": "on"
        }
        
        session = requests.Session()
        response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
        
        if response.status_code == 302:  # Redirect after successful login
            print("✅ Login successful (redirect)")
            return session
        else:
            print(f"❌ Login failed: {response.status_code}")
            print("Response:", response.text)
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_post_login_auth(session):
    """Test authentication after login"""
    print("\n🔍 Testing authentication after login...")
    try:
        response = session.get(f"{BASE_URL}/test-auth")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Post-login auth status: {data['status']}")
            if data['status'] == 'authenticated':
                print(f"   User: {data['email']}")
                print(f"   Paid: {data['is_paid']}")
                print(f"   Remaining analyses: {data['remaining_analyses']}")
                return True
            else:
                print("❌ User still not authenticated after login")
                return False
        else:
            print(f"❌ Post-login auth failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Post-login auth error: {e}")
        return False

def test_home_page(session):
    """Test access to home page after login"""
    print("\n🔍 Testing home page access after login...")
    try:
        response = session.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ Home page accessible after login")
            # Check if the page shows user-specific content
            if "Welcome back" in response.text or "remaining" in response.text:
                print("✅ Page shows user-specific content")
                return True
            else:
                print("⚠️ Page accessible but no user-specific content")
                return False
        else:
            print(f"❌ Home page access failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Home page test error: {e}")
        return False

def test_protected_route(session):
    """Test access to a protected route"""
    print("\n🔍 Testing protected route access...")
    try:
        response = session.get(f"{BASE_URL}/upgrade")
        if response.status_code == 200:
            print("✅ Protected route accessible")
            return True
        elif response.status_code == 302:
            print("❌ Protected route redirecting (not authenticated)")
            return False
        else:
            print(f"❌ Protected route failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Protected route test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Login Debug Tests\n")
    
    # Test 1: Check session configuration
    if not test_session_debug():
        print("\n❌ Session debug test failed. Check your Flask app.")
        return
    
    # Test 2: Check initial auth status
    initial_auth = test_auth_status()
    if initial_auth == 'authenticated':
        print("\n⚠️ User is already logged in. Testing logout first...")
        # You might want to test logout here
    
    # Test 3: Test login
    session = test_login()
    if not session:
        print("\n❌ Login test failed. Check your credentials and database.")
        return
    
    # Test 4: Check auth status after login
    if not test_post_login_auth(session):
        print("\n❌ Authentication failed after login. Check session configuration.")
        return
    
    # Test 5: Test home page access
    if not test_home_page(session):
        print("\n❌ Home page test failed. Check template rendering.")
        return
    
    # Test 6: Test protected route access
    if not test_protected_route(session):
        print("\n❌ Protected route test failed. Check authentication middleware.")
        return
    
    print("\n🎉 All login tests passed! Your authentication is working correctly.")
    print("\n💡 If you're still having issues:")
    print("1. Check browser console for JavaScript errors")
    print("2. Check Flask app logs for errors")
    print("3. Verify your .env file has FLASK_SECRET_KEY set")
    print("4. Check if cookies are being set in your browser")

if __name__ == "__main__":
    main()

