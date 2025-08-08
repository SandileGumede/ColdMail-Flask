# PitchAI Deployment Guide

## Recent Database Connection Fixes

### Issue: "Database does not support maximum retries and its waiting for the database"

This error was occurring because:

1. **SQLAlchemy Version Compatibility**: The app was using deprecated SQLAlchemy syntax (`db.engine.execute()`) that doesn't work with newer versions of SQLAlchemy.

2. **Startup Script Not Used**: The `startup.py` script wasn't being executed during deployment, so database initialization wasn't happening properly.

3. **Insufficient Error Handling**: The database connection retry logic wasn't providing enough information about what was failing.

### Fixes Applied

#### 1. SQLAlchemy Compatibility
- Updated all database connection code to use both old and new SQLAlchemy syntax
- Added fallback mechanisms for different SQLAlchemy versions
- Fixed `db.engine.execute()` calls to use proper connection handling

#### 2. Improved Startup Process
- Modified `Procfile` to run `startup.py` before starting Gunicorn
- Enhanced `startup.py` with better error reporting and retry logic
- Added database URL validation and format checking

#### 3. Better Error Handling
- Added specific error messages for different types of database failures
- Improved retry logic with exponential backoff
- Added comprehensive logging for debugging

## Deployment Files

### Procfile
```
web: python startup.py && gunicorn -c gunicorn.conf.py app:app
```

### startup.py
- Validates environment variables
- Checks database URL format
- Waits for database with retries
- Initializes database tables
- Provides detailed error messages

### gunicorn.conf.py
- Single worker for better session handling
- Increased timeouts for database operations
- Better logging and error handling

## Testing

### Local Testing
```bash
# Test database connection
python test_database.py

# Test startup process
python startup.py

# Test full application
python app.py
```

### Production Testing
After deployment, check these endpoints:
- `/health` - Overall application health
- `/test-db` - Database connection test
- `/check-db` - Database status and initialization
- `/deployment-status` - Full deployment status

## Environment Variables

### Required
- `FLASK_SECRET_KEY` - Secret key for Flask sessions

### Optional
- `DATABASE_URL` - Database connection string (PostgreSQL recommended for production)
- `OPENAI_API_KEY` - OpenAI API key for email analysis
- `PAYPAL_CLIENT_ID` - PayPal client ID for payments
- `PAYPAL_CLIENT_SECRET` - PayPal client secret for payments

## Database Configuration

### Development (SQLite)
- No `DATABASE_URL` needed
- Database file created in `instance/pitchai.db`

### Production (PostgreSQL)
- Set `DATABASE_URL` environment variable
- Format: `postgresql://username:password@host:port/database`
- Old format `postgres://` is automatically converted to `postgresql://`

## Troubleshooting

### Common Issues

1. **"Database does not support maximum retries"**
   - Check if `DATABASE_URL` is set correctly
   - Verify database credentials
   - Check if database service is running

2. **"Connection timeout"**
   - Database may be overloaded
   - Check database server status
   - Verify network connectivity

3. **"Authentication failed"**
   - Verify database username/password
   - Check if user has proper permissions

### Debug Commands

```bash
# Test database connection
python test_database.py

# Check environment variables
python -c "import os; print('DATABASE_URL:', os.environ.get('DATABASE_URL', 'Not set'))"

# Test Flask app import
python -c "from app import app; print('App imported successfully')"
```

## Render Deployment

1. Connect your repository to Render
2. Set environment variables in Render dashboard
3. Deploy using the Procfile
4. Monitor logs for any startup issues
5. Test the application endpoints

The startup script will now provide detailed information about what's happening during deployment, making it easier to diagnose any issues.
