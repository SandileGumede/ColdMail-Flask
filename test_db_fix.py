#!/usr/bin/env python3
"""
Test script to verify database compatibility fix
"""

def test_psycopg_imports():
    """Test if psycopg can be imported"""
    print("🧪 Testing PostgreSQL Adapter...")
    print("=" * 50)
    
    try:
        import psycopg
        print("✅ psycopg3 imported successfully")
        return True
    except ImportError as e:
        print(f"❌ psycopg3 import failed: {e}")
        
        try:
            import psycopg2
            print("✅ psycopg2 imported successfully (fallback)")
            return True
        except ImportError as e2:
            print(f"❌ psycopg2 import also failed: {e2}")
            return False

def test_database_compatibility():
    """Test database compatibility layer"""
    print("\n🔗 Testing Database Compatibility...")
    print("=" * 50)
    
    try:
        from db_compat import get_database_url, test_database_connection, PSYCOPG_VERSION
        
        print(f"PostgreSQL adapter version: {PSYCOPG_VERSION}")
        
        db_url = get_database_url()
        print(f"Database URL: {db_url}")
        
        success, message = test_database_connection(db_url)
        if success:
            print(f"✅ {message}")
            return True
        else:
            print(f"⚠️  {message}")
            return False
            
    except Exception as e:
        print(f"❌ Database compatibility test failed: {e}")
        return False

def test_flask_sqlalchemy():
    """Test Flask-SQLAlchemy with the new adapter"""
    print("\n🗄️ Testing Flask-SQLAlchemy...")
    print("=" * 50)
    
    try:
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy
        
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db = SQLAlchemy(app)
        
        with app.app_context():
            db.create_all()
            print("✅ Flask-SQLAlchemy works with new adapter")
            return True
            
    except Exception as e:
        print(f"❌ Flask-SQLAlchemy test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Database Compatibility Test")
    print("=" * 50)
    
    tests = [
        ("PostgreSQL Adapter Import", test_psycopg_imports),
        ("Database Compatibility", test_database_compatibility),
        ("Flask-SQLAlchemy", test_flask_sqlalchemy)
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
        print("\n🎉 All tests passed! Database compatibility is fixed.")
        print("✅ Your app should deploy successfully on Render!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("❌ There may still be database issues to resolve.")
    
    return passed == total

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
