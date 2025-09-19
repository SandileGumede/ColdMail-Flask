"""
Database compatibility layer for psycopg2/psycopg3
This handles the differences between psycopg2 and psycopg3
"""

try:
    # Try psycopg3 first (newer, more compatible)
    import psycopg
    from psycopg import sql
    print("✅ Using psycopg3 (modern PostgreSQL adapter)")
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        # Fallback to psycopg2
        import psycopg2
        from psycopg2 import sql
        print("✅ Using psycopg2 (legacy PostgreSQL adapter)")
        PSYCOPG_VERSION = 2
    except ImportError:
        print("❌ No PostgreSQL adapter found")
        PSYCOPG_VERSION = None

def get_database_url():
    """Get the database URL with proper formatting for the installed adapter"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        # Check for Supabase database URL
        supabase_url = os.environ.get('SUPABASE_DATABASE_URL')
        if supabase_url:
            database_url = supabase_url
        else:
            # Default to SQLite in instance folder
            return 'sqlite:///pitchai.db'
    
    # Fix for older PostgreSQL URLs
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    return database_url

def test_database_connection(database_url):
    """Test database connection with the available adapter"""
    if 'sqlite' in database_url:
        return True, "SQLite database (no connection test needed)"
    
    try:
        if PSYCOPG_VERSION == 3:
            # Test psycopg3 connection
            with psycopg.connect(database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
            return True, "psycopg3 connection successful"
        elif PSYCOPG_VERSION == 2:
            # Test psycopg2 connection
            conn = psycopg2.connect(database_url)
            cur = conn.cursor()
            cur.execute("SELECT 1")
            result = cur.fetchone()
            cur.close()
            conn.close()
            return True, "psycopg2 connection successful"
        else:
            return False, "No PostgreSQL adapter available"
    except Exception as e:
        return False, f"Database connection failed: {e}"

if __name__ == "__main__":
    # Test the database connection
    db_url = get_database_url()
    success, message = test_database_connection(db_url)
    print(f"Database URL: {db_url}")
    print(f"Connection test: {message}")
