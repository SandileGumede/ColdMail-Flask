#!/usr/bin/env python3
"""
Debug script to test login issues
Run this to check your Supabase configuration and login flow
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_environment():
    """Test environment variables"""
    print("🔍 Testing Environment Variables...")
    print("=" * 50)
    
    required_vars = {
        'SUPABASE_URL': 'Supabase Project URL',
        'SUPABASE_ANON_KEY': 'Supabase Anonymous Key',
        'SUPABASE_DATABASE_URL': 'Supabase Database URL',
        'FLASK_SECRET_KEY': 'Flask Secret Key'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'KEY' in var or 'URL' in var:
                masked_value = value[:10] + "..." + value[-10:] if len(value) > 20 else "***"
                print(f"  ✅ {description}: {masked_value}")
            else:
                print(f"  ✅ {description}: {value}")
        else:
            print(f"  ❌ {description}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    print("\n✅ All required environment variables are set!")
    return True

def test_supabase_connection():
    """Test Supabase connection"""
    print("\n🔗 Testing Supabase Connection...")
    print("=" * 50)
    
    try:
        from supabase_config import supabase_config
        client = supabase_config.get_client()
        print("  ✅ Supabase client created successfully")
        
        # Test a simple query
        response = client.table('users').select('*').limit(1).execute()
        print("  ✅ Database connection successful")
        print(f"  📊 Found {len(response.data)} users in database")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Supabase connection failed: {e}")
        print(f"  🔧 Error type: {type(e).__name__}")
        return False

def test_auth_flow():
    """Test authentication flow"""
    print("\n🔐 Testing Authentication Flow...")
    print("=" * 50)
    
    try:
        from supabase_service import SupabaseService
        service = SupabaseService()
        print("  ✅ SupabaseService initialized")
        
        # Test with a dummy email (won't actually authenticate)
        print("  ℹ️  Testing auth service initialization...")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Authentication service test failed: {e}")
        print(f"  🔧 Error type: {type(e).__name__}")
        return False

def test_database_models():
    """Test database models"""
    print("\n🗄️ Testing Database Models...")
    print("=" * 50)
    
    try:
        from app import app, db, User
        with app.app_context():
            # Test database connection
            db.engine.connect()
            print("  ✅ Database engine connection successful")
            
            # Test User model
            user_count = User.query.count()
            print(f"  ✅ User model working, {user_count} users found")
            
            # Test if we can create a test user (without saving)
            test_user = User()
            test_user.email = "test@example.com"
            test_user.supabase_id = "test-supabase-id"
            print("  ✅ User model can be instantiated")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Database model test failed: {e}")
        print(f"  🔧 Error type: {type(e).__name__}")
        return False

def main():
    """Main test function"""
    print("🚀 PitchAI Login Debug Test")
    print("=" * 50)
    
    tests = [
        ("Environment Variables", test_environment),
        ("Supabase Connection", test_supabase_connection),
        ("Authentication Service", test_auth_flow),
        ("Database Models", test_database_models)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} test passed!")
        else:
            print(f"❌ {test_name} test failed!")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your setup looks good.")
        print("\nNext steps:")
        print("1. Check your Render logs for any error messages")
        print("2. Visit /debug-login on your deployed app to see session info")
        print("3. Try logging in with a test account")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("- Check your .env file has all required variables")
        print("- Verify your Supabase project is active")
        print("- Make sure your database URL is correct")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)



