#!/usr/bin/env python3
"""
Test script for PitchAI application
Tests database connection, user creation, and login functionality
"""

import os
import sys
from app import app, db, User
from werkzeug.security import generate_password_hash

def test_database():
    """Test database connection and basic operations"""
    print("Testing database connection...")
    
    try:
        with app.app_context():
            # Test connection
            db.engine.execute('SELECT 1')
            print("✓ Database connection successful")
            
            # Create tables
            db.create_all()
            print("✓ Database tables created")
            
            # Test User model
            user_count = User.query.count()
            print(f"✓ User model working (current users: {user_count})")
            
            return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_user_creation():
    """Test user creation and authentication"""
    print("\nTesting user creation and authentication...")
    
    try:
        with app.app_context():
            # Create test user
            test_email = "test@example.com"
            test_password = "testpassword123"
            
            # Check if test user exists
            existing_user = User.query.filter_by(email=test_email).first()
            if existing_user:
                db.session.delete(existing_user)
                db.session.commit()
                print("✓ Removed existing test user")
            
            # Create new test user
            user = User()
            user.email = test_email
            user.set_password(test_password)
            
            db.session.add(user)
            db.session.commit()
            print("✓ Test user created successfully")
            
            # Test password verification
            if user.check_password(test_password):
                print("✓ Password verification working")
            else:
                print("✗ Password verification failed")
                return False
            
            # Test user methods
            remaining = user.get_remaining_analyses()
            print(f"✓ User methods working (remaining analyses: {remaining})")
            
            # Clean up
            db.session.delete(user)
            db.session.commit()
            print("✓ Test user cleaned up")
            
            return True
            
    except Exception as e:
        print(f"✗ User creation test failed: {e}")
        return False

def test_flask_app():
    """Test Flask app configuration"""
    print("\nTesting Flask app configuration...")
    
    try:
        # Test app configuration
        if app.config['SECRET_KEY']:
            print("✓ Secret key configured")
        else:
            print("✗ Secret key not configured")
            return False
        
        # Test database URL
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"✓ Database URL: {db_url}")
        
        # Test environment variables
        env_vars = {
            'FLASK_SECRET_KEY': os.environ.get('FLASK_SECRET_KEY'),
            'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
            'DATABASE_URL': os.environ.get('DATABASE_URL')
        }
        
        for var, value in env_vars.items():
            if value:
                print(f"✓ {var} configured")
            else:
                print(f"⚠ {var} not configured (optional)")
        
        return True
        
    except Exception as e:
        print(f"✗ Flask app test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=== PitchAI Application Test ===\n")
    
    tests = [
        test_flask_app,
        test_database,
        test_user_creation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"=== Test Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("✓ All tests passed! Application is ready for deployment.")
        return 0
    else:
        print("✗ Some tests failed. Please fix the issues before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())


