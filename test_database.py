#!/usr/bin/env python3
"""
Database connection test script for PitchAI
Run this to diagnose database connectivity issues
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test database connection without Flask app context"""
    print("=== Database Connection Test ===\n")
    
    # Check environment variables
    database_url = os.environ.get('DATABASE_URL')
    print(f"DATABASE_URL: {'Set' if database_url else 'Not set'}")
    
    if database_url:
        # Show first part of URL for debugging
        safe_url = database_url[:20] + "..." if len(database_url) > 20 else database_url
        print(f"URL preview: {safe_url}")
        
        # Check URL format
        if database_url.startswith('postgres://'):
            print("⚠ Old PostgreSQL format detected (postgres://)")
            corrected_url = database_url.replace('postgres://', 'postgresql://', 1)
            print(f"Corrected format: {corrected_url[:20]}...")
        elif database_url.startswith('postgresql://'):
            print("✓ PostgreSQL format is correct")
        elif database_url.startswith('sqlite://'):
            print("✓ SQLite format is correct")
        else:
            print("⚠ Unknown database URL format")
    
    # Test basic connectivity
    print("\n--- Testing Database Connectivity ---")
    
    try:
        # Try to import SQLAlchemy and test connection
        from sqlalchemy import create_engine, text
        
        if database_url:
            # Fix PostgreSQL URL if needed
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            engine = create_engine(database_url, echo=False)
            
            # Test connection
            with engine.connect() as connection:
                result = connection.execute(text('SELECT 1'))
                print("✓ Database connection successful")
                result.close()
                
        else:
            print("⚠ No DATABASE_URL, using SQLite")
            engine = create_engine('sqlite:///test.db', echo=False)
            with engine.connect() as connection:
                result = connection.execute(text('SELECT 1'))
                print("✓ SQLite connection successful")
                result.close()
                
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Provide specific guidance based on error type
        error_msg = str(e).lower()
        if "connection" in error_msg:
            print("\n→ Connection issue detected:")
            print("  - Check if database service is running")
            print("  - Verify network connectivity")
            print("  - Check firewall settings")
        elif "authentication" in error_msg:
            print("\n→ Authentication issue detected:")
            print("  - Verify database credentials")
            print("  - Check username/password in DATABASE_URL")
        elif "does not exist" in error_msg:
            print("\n→ Database does not exist:")
            print("  - Database may need to be created")
            print("  - Check database name in URL")
        elif "timeout" in error_msg:
            print("\n→ Connection timeout:")
            print("  - Database may be overloaded")
            print("  - Check database server status")
        
        return False
    
    return True

def test_flask_app_import():
    """Test if Flask app can be imported"""
    print("\n--- Testing Flask App Import ---")
    
    try:
        from app import app, db
        print("✓ Flask app imported successfully")
        return True
    except Exception as e:
        print(f"✗ Flask app import failed: {e}")
        return False

def test_flask_database():
    """Test database through Flask app context"""
    print("\n--- Testing Flask Database Context ---")
    
    try:
        from app import app, db, User
        
        with app.app_context():
            # Test database connection using the correct SQLAlchemy syntax
            try:
                # Try newer SQLAlchemy syntax first
                with db.engine.connect() as connection:
                    result = connection.execute(db.text('SELECT 1'))
                    print("✓ Flask database connection successful (new syntax)")
                    result.close()
            except AttributeError:
                # Fall back to older SQLAlchemy syntax
                result = db.engine.execute('SELECT 1')
                print("✓ Flask database connection successful (legacy syntax)")
                result.close()
            
            # Test table creation
            db.create_all()
            print("✓ Database tables created/verified")
            
            # Test User model
            user_count = User.query.count()
            print(f"✓ User model working (users: {user_count})")
            
        return True
        
    except Exception as e:
        print(f"✗ Flask database test failed: {e}")
        return False

if __name__ == "__main__":
    print("PitchAI Database Diagnostic Tool\n")
    
    # Test basic database connection
    db_ok = test_database_connection()
    
    # Test Flask app import
    flask_ok = test_flask_app_import()
    
    # Test Flask database context
    flask_db_ok = test_flask_database() if flask_ok else False
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Database Connection: {'✓' if db_ok else '✗'}")
    print(f"Flask App Import: {'✓' if flask_ok else '✗'}")
    print(f"Flask Database: {'✓' if flask_db_ok else '✗'}")
    
    if all([db_ok, flask_ok, flask_db_ok]):
        print("\n✓ All tests passed! Database is ready.")
    else:
        print("\n✗ Some tests failed. Check the errors above.")
        sys.exit(1)
