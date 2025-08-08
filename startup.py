#!/usr/bin/env python3
"""
Startup script for PitchAI production deployment
Ensures database is properly initialized before starting the server
"""

import os
import sys
import time
from app import app, db, User

def wait_for_database(max_retries=5, delay=2):
    """Wait for database to be available"""
    print("Waiting for database to be available...")
    
    for attempt in range(max_retries):
        try:
            with app.app_context():
                db.engine.execute('SELECT 1')
                print("✓ Database is available")
                return True
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries}: Database not ready ({e})")
            if attempt < max_retries - 1:
                time.sleep(delay)
    
    print("✗ Database not available after maximum retries")
    return False

def initialize_production():
    """Initialize the application for production deployment"""
    print("Initializing PitchAI for production...")
    
    # Wait for database
    if not wait_for_database():
        return False
    
    try:
        with app.app_context():
            # Create tables if they don't exist
            db.create_all()
            print("✓ Database tables created/verified")
            
            # Test User model
            user_count = User.query.count()
            print(f"✓ User model working (current users: {user_count})")
            
            # Test basic functionality
            test_user = User.query.first()
            if test_user:
                remaining = test_user.get_remaining_analyses()
                print(f"✓ User methods working (sample user has {remaining} analyses remaining)")
            
            print("✓ Production initialization complete")
            return True
            
    except Exception as e:
        print(f"✗ Production initialization failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

def check_environment():
    """Check if required environment variables are set"""
    print("Checking environment configuration...")
    
    required_vars = ['FLASK_SECRET_KEY']
    optional_vars = ['OPENAI_API_KEY', 'DATABASE_URL', 'PAYPAL_CLIENT_ID', 'PAYPAL_CLIENT_SECRET']
    
    missing_required = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_required.append(var)
    
    if missing_required:
        print(f"✗ Missing required environment variables: {', '.join(missing_required)}")
        return False
    
    print("✓ Required environment variables configured")
    
    for var in optional_vars:
        if os.environ.get(var):
            print(f"✓ {var} configured")
        else:
            print(f"⚠ {var} not configured (optional)")
    
    return True

if __name__ == "__main__":
    print("=== PitchAI Production Startup ===\n")
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Initialize production
    success = initialize_production()
    if not success:
        print("\n✗ Startup failed. Check logs for details.")
        sys.exit(1)
    
    print("\n✓ Startup successful! Application is ready to serve requests.") 