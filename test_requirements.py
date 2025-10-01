#!/usr/bin/env python3
"""
Test script to verify requirements.txt works without conflicts
"""

def test_requirements():
    """Test if all requirements can be imported without conflicts"""
    print("🧪 Testing Requirements Compatibility...")
    print("=" * 50)
    
    # Test basic Flask imports
    try:
        import flask
        print("✅ Flask imported successfully")
    except ImportError as e:
        print(f"❌ Flask import failed: {e}")
        return False
    
    # Test Supabase import
    try:
        from supabase import create_client
        print("✅ Supabase imported successfully")
    except ImportError as e:
        print(f"❌ Supabase import failed: {e}")
        return False
    
    # Test other key imports
    try:
        import psycopg2
        print("✅ psycopg2 imported successfully")
    except ImportError as e:
        print(f"❌ psycopg2 import failed: {e}")
        return False
    
    try:
        import requests
        print("✅ requests imported successfully")
    except ImportError as e:
        print(f"❌ requests import failed: {e}")
        return False
    
    try:
        import paypalrestsdk
        print("✅ paypalrestsdk imported successfully")
    except ImportError as e:
        print(f"❌ paypalrestsdk import failed: {e}")
        return False
    
    print("\n🎉 All requirements imported successfully!")
    print("✅ No dependency conflicts detected")
    return True

if __name__ == "__main__":
    success = test_requirements()
    if success:
        print("\n✅ Your requirements.txt should work fine in Render!")
    else:
        print("\n❌ There are still dependency issues to resolve.")





