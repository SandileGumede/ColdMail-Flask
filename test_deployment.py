#!/usr/bin/env python3
"""
Deployment test script for PitchAI
Run this before deploying to verify everything is working
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_environment():
    """Test environment variables"""
    print("=== Environment Test ===\n")
    
    required_vars = ['FLASK_SECRET_KEY']
    optional_vars = ['DATABASE_URL', 'OPENAI_API_KEY', 'PAYPAL_CLIENT_ID', 'PAYPAL_CLIENT_SECRET']
    
    all_good = True
    
    for var in required_vars:
        if os.environ.get(var):
            print(f"✓ {var}: Set")
        else:
            print(f"✗ {var}: Missing (REQUIRED)")
            all_good = False
    
    for var in optional_vars:
        if os.environ.get(var):
            print(f"✓ {var}: Set")
        else:
            print(f"⚠ {var}: Not set (optional)")
    
    return all_good

def test_imports():
    """Test if all required modules can be imported"""
    print("\n=== Import Test ===\n")
    
    modules = [
        ('flask', 'Flask'),
        ('flask_sqlalchemy', 'SQLAlchemy'),
        ('flask_login', 'LoginManager'),
        ('werkzeug.security', 'generate_password_hash'),
        ('sqlalchemy', 'create_engine'),
        ('requests', 'get'),
        ('paypalrestsdk', 'configure')
    ]
    
    all_good = True
    
    for module_name, item_name in modules:
        try:
            __import__(module_name)
            print(f"✓ {module_name}: Imported successfully")
        except ImportError as e:
            print(f"✗ {module_name}: Import failed - {e}")
            all_good = False
    
    return all_good

def test_app_creation():
    """Test if the Flask app can be created"""
    print("\n=== App Creation Test ===\n")
    
    try:
        from app import app, db, User
        print("✓ Flask app created successfully")
        print(f"✓ Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"✓ Secret key: {'Set' if app.config['SECRET_KEY'] else 'Not set'}")
        return True
    except Exception as e:
        print(f"✗ Flask app creation failed: {e}")
        return False

def test_database():
    """Test database connection and operations"""
    print("\n=== Database Test ===\n")
    
    try:
        from app import app, db, User
        
        with app.app_context():
            # Test connection
            try:
                with db.engine.connect() as connection:
                    result = connection.execute(db.text('SELECT 1'))
                    result.close()
                print("✓ Database connection successful")
            except AttributeError:
                result = db.engine.execute('SELECT 1')
                result.close()
                print("✓ Database connection successful (legacy)")
            
            # Test table creation
            db.create_all()
            print("✓ Database tables created/verified")
            
            # Test User model
            user_count = User.query.count()
            print(f"✓ User model working (users: {user_count})")
            
            # Test user creation
            test_user = User.query.first()
            if test_user:
                remaining = test_user.get_remaining_analyses()
                print(f"✓ User methods working (sample user has {remaining} analyses)")
            
        return True
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_routes():
    """Test if routes can be accessed"""
    print("\n=== Route Test ===\n")
    
    try:
        from app import app
        
        # Test basic routes
        routes_to_test = ['/', '/login', '/signup', '/health']
        
        with app.test_client() as client:
            for route in routes_to_test:
                try:
                    response = client.get(route)
                    if response.status_code in [200, 302]:  # 302 is redirect for login
                        print(f"✓ {route}: {response.status_code}")
                    else:
                        print(f"⚠ {route}: {response.status_code}")
                except Exception as e:
                    print(f"✗ {route}: Error - {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Route test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("PitchAI Deployment Test Suite\n")
    print("This script tests all components before deployment.\n")
    
    tests = [
        ("Environment Variables", test_environment),
        ("Module Imports", test_imports),
        ("App Creation", test_app_creation),
        ("Database", test_database),
        ("Routes", test_routes)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n=== Test Summary ===")
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your app is ready for deployment.")
        return True
    else:
        print("\n❌ Some tests failed. Please fix the issues before deploying.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
