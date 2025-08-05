#!/usr/bin/env python3
"""
Startup script for PitchAI production deployment
Ensures database is properly initialized before starting the server
"""

import os
import sys
from app import app, db, User

def initialize_production():
    """Initialize the application for production deployment"""
    print("Initializing PitchAI for production...")
    
    try:
        with app.app_context():
            # Test database connection
            db.engine.execute('SELECT 1')
            print("✓ Database connection successful")
            
            # Create tables if they don't exist
            db.create_all()
            print("✓ Database tables created/verified")
            
            # Test User model
            user_count = User.query.count()
            print(f"✓ User model working (current users: {user_count})")
            
            print("✓ Production initialization complete")
            return True
            
    except Exception as e:
        print(f"✗ Production initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = initialize_production()
    if not success:
        sys.exit(1) 