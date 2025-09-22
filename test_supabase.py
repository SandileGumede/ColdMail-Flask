#!/usr/bin/env python3
"""
Test script for Supabase integration
Run this to verify your Supabase setup is working correctly
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_supabase_connection():
    """Test Supabase connection and configuration"""
    print("🔍 Testing Supabase Integration...")
    print("=" * 50)
    
    # Check environment variables
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'SUPABASE_DATABASE_URL'
    ]
    
    print("📋 Checking Environment Variables:")
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'KEY' in var or 'URL' in var:
                masked_value = value[:10] + "..." + value[-10:] if len(value) > 20 else "***"
                print(f"  ✅ {var}: {masked_value}")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file and SUPABASE_SETUP.md for guidance.")
        return False
    
    print("\n🔗 Testing Supabase Connection:")
    try:
        from supabase_config import supabase_config
        client = supabase_config.get_client()
        print("  ✅ Supabase client created successfully")
        
        # Test a simple query
        response = client.table('users').select('*').limit(1).execute()
        print("  ✅ Database connection successful")
        
    except Exception as e:
        print(f"  ❌ Supabase connection failed: {e}")
        return False
    
    print("\n🗄️ Testing Database Models:")
    try:
        from app import app, db, User
        with app.app_context():
            # Test database connection
            db.engine.connect()
            print("  ✅ Database engine connection successful")
            
            # Test User model
            user_count = User.query.count()
            print(f"  ✅ User model working, {user_count} users found")
            
    except Exception as e:
        print(f"  ❌ Database model test failed: {e}")
        return False
    
    print("\n🎉 All tests passed! Supabase integration is ready.")
    print("\nNext steps:")
    print("1. Start your Flask app: python app.py")
    print("2. Visit http://localhost:5000 to test signup/login")
    print("3. Check your Supabase dashboard for new users")
    
    return True

def test_auth_flow():
    """Test authentication flow (optional)"""
    print("\n🔐 Testing Authentication Flow:")
    print("=" * 50)
    
    try:
        from supabase_service import SupabaseService
        service = SupabaseService()
        print("  ✅ SupabaseService initialized")
        
        # Note: We won't actually test signup/login here to avoid creating test users
        print("  ℹ️  Authentication service ready (manual testing required)")
        
    except Exception as e:
        print(f"  ❌ Authentication service test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 PitchAI Supabase Integration Test")
    print("=" * 50)
    
    # Test basic connection
    if test_supabase_connection():
        # Test auth service
        test_auth_flow()
        print("\n✅ Integration test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Integration test failed. Please check your configuration.")
        sys.exit(1)



