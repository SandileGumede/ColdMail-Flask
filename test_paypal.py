#!/usr/bin/env python3
"""
Test script for PayPal integration endpoints
Run this to verify your PayPal integration is working correctly
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

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_login():
    """Test user login to get session"""
    print("🔍 Testing user login...")
    try:
        # First try to login
        login_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        session = requests.Session()
        response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
        
        if response.status_code == 302:  # Redirect after successful login
            print("✅ Login successful")
            return session
        else:
            print(f"❌ Login failed: {response.status_code}")
            print("Response:", response.text)
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_paypal_checkout_page(session):
    """Test access to PayPal checkout page"""
    print("🔍 Testing PayPal checkout page access...")
    try:
        response = session.get(f"{BASE_URL}/paypal-checkout")
        if response.status_code == 200:
            print("✅ PayPal checkout page accessible")
            return True
        else:
            print(f"❌ PayPal checkout page access failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ PayPal checkout page error: {e}")
        return False

def test_upgrade_page(session):
    """Test access to upgrade page"""
    print("🔍 Testing upgrade page access...")
    try:
        response = session.get(f"{BASE_URL}/upgrade")
        if response.status_code == 200:
            print("✅ Upgrade page accessible")
            return True
        else:
            print(f"❌ Upgrade page access failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Upgrade page error: {e}")
        return False

def test_paypal_order_creation(session):
    """Test PayPal order creation endpoint"""
    print("🔍 Testing PayPal order creation...")
    try:
        order_data = {
            "cart": [
                {
                    "id": "pitchai_upgrade",
                    "quantity": "1"
                }
            ]
        }
        
        response = session.post(
            f"{BASE_URL}/api/orders",
            json=order_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Order creation successful: {data.get('id', 'No ID')}")
            return data.get('id')
        else:
            print(f"❌ Order creation failed: {response.status_code}")
            print("Response:", response.text)
            return None
    except Exception as e:
        print(f"❌ Order creation error: {e}")
        return None

def test_environment_variables():
    """Test if required environment variables are set"""
    print("🔍 Testing environment variables...")
    
    required_vars = [
        "PAYPAL_CLIENT_ID",
        "PAYPAL_CLIENT_SECRET",
        "FLASK_SECRET_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def main():
    """Run all tests"""
    print("🚀 Starting PayPal Integration Tests\n")
    
    # Test environment variables first
    if not test_environment_variables():
        print("\n❌ Environment variables test failed. Please check your .env file.")
        return
    
    # Test health check
    if not test_health_check():
        print("\n❌ Health check failed. Make sure your Flask app is running.")
        return
    
    # Test login
    session = test_login()
    if not session:
        print("\n❌ Login failed. Please check your test user credentials.")
        return
    
    # Test page access
    if not test_paypal_checkout_page(session):
        print("\n❌ PayPal checkout page test failed.")
        return
    
    if not test_upgrade_page(session):
        print("\n❌ Upgrade page test failed.")
        return
    
    # Test order creation
    order_id = test_paypal_order_creation(session)
    if not order_id:
        print("\n❌ PayPal order creation test failed.")
        return
    
    print("\n🎉 All tests passed! Your PayPal integration is working correctly.")
    print(f"📝 Created test order: {order_id}")
    print("\n💡 Next steps:")
    print("1. Test the PayPal button on your checkout page")
    print("2. Use PayPal sandbox credentials for testing")
    print("3. Verify that user accounts are upgraded after payment")

if __name__ == "__main__":
    main()

