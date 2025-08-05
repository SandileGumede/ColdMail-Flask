#!/usr/bin/env python3
"""
Test script to verify authentication functionality
"""

import requests
import json

def test_auth_forms(base_url="http://localhost:5000"):
    """Test authentication forms and endpoints"""
    
    print("Testing authentication functionality...")
    
    # Test 1: Check if login page loads
    try:
        response = requests.get(f"{base_url}/login")
        if response.status_code == 200:
            print("✓ Login page loads successfully")
        else:
            print(f"✗ Login page failed to load: {response.status_code}")
    except Exception as e:
        print(f"✗ Error accessing login page: {e}")
    
    # Test 2: Check if signup page loads
    try:
        response = requests.get(f"{base_url}/signup")
        if response.status_code == 200:
            print("✓ Signup page loads successfully")
        else:
            print(f"✗ Signup page failed to load: {response.status_code}")
    except Exception as e:
        print(f"✗ Error accessing signup page: {e}")
    
    # Test 3: Check deployment status
    try:
        response = requests.get(f"{base_url}/deployment-status")
        if response.status_code == 200:
            data = response.json()
            print("✓ Deployment status endpoint working")
            print(f"  Database status: {data.get('database', {}).get('status', 'unknown')}")
            print(f"  User count: {data.get('database', {}).get('user_count', 0)}")
        else:
            print(f"✗ Deployment status failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error checking deployment status: {e}")
    
    # Test 4: Check health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✓ Health check endpoint working")
        else:
            print(f"✗ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error checking health: {e}")

if __name__ == "__main__":
    # Test local server
    test_auth_forms()
    
    # Uncomment to test production server
    # test_auth_forms("https://your-app-name.onrender.com") 