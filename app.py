from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_session import Session
from models import db, User
from supabase_service import SupabaseService
import re
import os
import requests
import hmac
import hashlib
import base64
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import json

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
print("OPENAI_API_KEY loaded:", OPENAI_API_KEY is not None)
print("GOOGLE_API_KEY loaded:", GOOGLE_API_KEY is not None)

GENERATED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'generated')
os.makedirs(GENERATED_DIR, exist_ok=True)

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")

# Session configuration - more flexible for development and production
if os.environ.get('FLASK_ENV') == 'production':
    # Production settings
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_PERMANENT'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
else:
    # Development settings
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_PERMANENT'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Configure Flask-Session to use database storage
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY'] = db
app.config['SESSION_SQLALCHEMY_TABLE'] = 'sessions'
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'pitchai:'
# Use environment variable for database URL (for production) or default to SQLite
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    # Check for Supabase database URL
    supabase_url = os.environ.get('SUPABASE_DATABASE_URL')
    if supabase_url:
        database_url = supabase_url
    else:
        # Default to SQLite in instance folder
        database_url = 'sqlite:///pitchai.db'
elif database_url.startswith('postgres://'):
    # Fix for older PostgreSQL URLs
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
print(f"Using database: {database_url}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Production database settings
if 'postgresql' in database_url or 'postgres' in database_url:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 30,
        'max_overflow': 0,
        'pool_size': 10
    }
else:
    # SQLite settings for development
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20
    }

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
setattr(login_manager, 'login_view', 'login')
login_manager.login_message = 'Please log in to access this feature.'

# Initialize Supabase service with fallback
try:
    supabase_service = SupabaseService()
    print("✅ Supabase service initialized")
except Exception as e:
    print(f"⚠️  Supabase service initialization failed: {e}")
    print("   Falling back to local authentication only...")
    try:
        from no_supabase_mode import NoSupabaseService
        supabase_service = NoSupabaseService()
        print("✅ Local authentication service initialized")
    except Exception as e2:
        print(f"❌ Local authentication service also failed: {e2}")
        print("   Authentication will be disabled")
        supabase_service = None

# Add request logging middleware
@app.before_request
def log_request_info():
    print(f"Request: {request.method} {request.path}")
    print(f"User authenticated: {current_user.is_authenticated}")
    if current_user.is_authenticated:
        print(f"Current user: {current_user.email}")
    print(f"Session ID: {session.get('_id', 'No session ID')}")
    print(f"Session user ID: {session.get('_user_id', 'No user ID')}")
    print("---")

# Ensure database is initialized in production
def ensure_db_initialized():
    """Ensure database is initialized, especially important for production"""
    max_retries = 5
    delay = 2
    
    for attempt in range(max_retries):
        try:
            with app.app_context():
                # Test if tables exist by trying to query
                try:
                    User.query.first()
                    print("✓ Database tables already exist")
                    return True
                except Exception as table_error:
                    print(f"Attempt {attempt + 1}/{max_retries}: Creating database tables...")
                    db.create_all()
                    print("✓ Database tables created successfully")
                    return True
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries}: Database initialization error: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("✗ Database initialization failed after maximum retries")
                return False
    
    return False

def ensure_slideshow_columns():
    """Add slideshow generation columns to existing user table if missing."""
    try:
        with app.app_context():
            from sqlalchemy import inspect as sa_inspect
            inspector = sa_inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user')]
            if 'slideshow_generations_used' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN slideshow_generations_used INTEGER DEFAULT 0'))
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN slideshow_generation_reset TIMESTAMP'))
                    conn.commit()
                print("Added slideshow generation columns to user table")
    except Exception as e:
        print(f"Slideshow column check (non-critical): {e}")

# Initialize database on startup
if not ensure_db_initialized():
    print("Warning: Database initialization failed, but continuing startup...")
ensure_slideshow_columns()

# Initialize Flask-Session after database is configured
Session(app)

# --- Main Application Routes ---
@app.route("/login/process", methods=["GET", "POST"])
def user_login():
    """Legacy auth route: forward to canonical /login endpoint."""
    if request.method == "POST":
        return redirect(url_for("login"), code=307)
    return redirect(url_for("login"))

@app.route("/signup/process", methods=["GET", "POST"])
def signup_user():
    """Legacy auth route: forward to canonical /signup endpoint."""
    if request.method == "POST":
        return redirect(url_for("signup"), code=307)
    return redirect(url_for("signup"))

@login_manager.user_loader
def load_user(user_id):
    try:
        user = User.query.get(int(user_id))
        if user:
            print(f"User loader: Loaded user {user.email} (ID: {user_id})")
        else:
            print(f"User loader: No user found for ID {user_id}")
        return user
    except Exception as e:
        print(f"User loader error: {e}")
        return None

# --- Helper Functions ---
IMAGE_VIDEO_MODELS = {
    'midjourney': 'Midjourney (Image)',
    'dalle3': 'DALL-E 3 (Image)',
    'stable_diffusion': 'Stable Diffusion XL (Image)',
    'flux': 'Flux (Image)',
    'leonardo': 'Leonardo AI (Image)',
    'ideogram': 'Ideogram (Image)',
    'imagen': 'Google Nano Banana/Imagen (Image)',
    'veo': 'Google Veo (Video)',
    'runway': 'Runway Gen-3 (Video)',
}

# --- Authentication Routes ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            user_name = request.form.get('user_name', '').strip()
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            print(f"Signup attempt for email: {email}, username: {user_name}")  # Debug logging
            
            # Validate input
            if not email or not password or not user_name:
                flash('Please fill in all fields.')
                return render_template('auth/signup.html')
            
            # Validate username
            if len(user_name) < 3:
                flash('Username must be at least 3 characters long.')
                return render_template('auth/signup.html')
            
            if len(user_name) > 12:
                flash('Username must be 12 characters or less.')
                return render_template('auth/signup.html')
            
            # Validate username format (letters, numbers, underscores only)
            if not re.match(r'^[a-zA-Z0-9_]+$', user_name):
                flash('Username can only contain letters, numbers, and underscores.')
                return render_template('auth/signup.html')
            
            if password != confirm_password:
                flash('Passwords do not match.')
                return render_template('auth/signup.html')
            
            if len(password) < 6:
                flash('Password must be at least 6 characters long.')
                return render_template('auth/signup.html')
            
            # Check if email already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email already registered. Please login.')
                return redirect(url_for('login'))
            
            # Check if username already exists
            existing_username = User.query.filter_by(user_name=user_name).first()
            if existing_username:
                flash('Username already taken. Please choose another.')
                return render_template('auth/signup.html')
            
            # Create new user with Supabase (if available)
            if supabase_service and supabase_service.is_available:
                result = supabase_service.sign_up(email, password, user_name)
            else:
                print("Supabase not available, using local authentication only")
                # Fallback to local user creation
                user = User()
                user.email = email
                user.user_name = user_name
                user.set_password(password)
                
                db.session.add(user)
                db.session.commit()
                
                result = {"success": True, "user": user}
            
            if result['success']:
                user = result['user']
                print(f"User created successfully: {user.id}")  # Debug logging
                
                login_user(user, remember=True)
                
                # Store user ID in session for database session tracking
                session['user_id'] = user.id
                session['login_time'] = datetime.utcnow().isoformat()
                session.permanent = True
                
                print(f"Session data after signup: {dict(session)}")
                
                flash('Account created! You have 6 free prompt improvements. Start optimizing your prompts now.')
                return redirect(url_for('home'))
            else:
                flash(f'Error creating account: {result.get("error", "Unknown error")}')
                return render_template('auth/signup.html')
            
        except Exception as e:
            db.session.rollback()
            print(f"Signup error: {e}")  # Debug logging
            flash('Error creating account. Please try again.')
            return render_template('auth/signup.html')
    
    return render_template('auth/signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Debug: Print current session state
    print(f"LOGIN: Method={request.method}, Session={dict(session)}, Authenticated={current_user.is_authenticated}")
    
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            remember = request.form.get('remember') == 'on'
            
            print(f"LOGIN: Attempt for email: {email}")  # Debug logging
            
            # Validate input
            if not email or not password:
                flash('Please fill in all fields.')
                return render_template('auth/login.html')
            
            # Try Supabase authentication first (if available)
            print(f"LOGIN: Supabase available: {supabase_service and supabase_service.is_available}")
            if supabase_service and supabase_service.is_available:
                try:
                    result = supabase_service.sign_in(email, password)
                    print(f"LOGIN: Supabase result: success={result.get('success')}, error={result.get('error', 'None')}")
                except Exception as supabase_error:
                    print(f"LOGIN: Supabase exception: {supabase_error}")
                    result = {"success": False, "error": str(supabase_error)}
            else:
                print("LOGIN: Supabase not available, will try local auth")
                result = {"success": False, "error": "Supabase not available"}
            
            if result['success']:
                user = result['user']
                print(f"LOGIN: User found: {user.email} (ID: {user.id})")
                
                # Login successful - use login_user
                try:
                    login_user(user, remember=remember)
                    print(f"LOGIN: login_user() completed, authenticated={current_user.is_authenticated}")
                except Exception as login_err:
                    print(f"LOGIN: login_user() FAILED: {login_err}")
                    raise login_err
                
                # Set session as permanent if remember is checked
                if remember:
                    session.permanent = True
                
                # Store user ID in session for database session tracking
                session['user_id'] = user.id
                session['login_time'] = datetime.utcnow().isoformat()
                
                # Update user last login
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                print(f"LOGIN: SUCCESS - User {user.id}, Session: {dict(session)}")
                
                flash(f'Welcome back! You have {user.get_remaining_analyses()} prompt improvements remaining.')
                return redirect(url_for('home'))
            else:
                print(f"LOGIN: Supabase failed, trying local auth fallback")
                
                # Fallback to local authentication for existing users
                user = User.query.filter_by(email=email).first()
                print(f"LOGIN: Local user lookup: {user.email if user else 'NOT FOUND'}")
                
                if user:
                    print(f"LOGIN: User has supabase_id: {user.supabase_id is not None}")
                    if user.check_password(password):
                        print(f"LOGIN: Password check PASSED")
                        try:
                            login_user(user, remember=remember)
                            print(f"LOGIN: login_user() completed for local auth")
                        except Exception as login_err:
                            print(f"LOGIN: login_user() FAILED: {login_err}")
                            raise login_err
                        
                        if remember:
                            session.permanent = True
                        
                        session['user_id'] = user.id
                        session['login_time'] = datetime.utcnow().isoformat()
                        
                        user.last_login = datetime.utcnow()
                        db.session.commit()
                        
                        print(f"LOGIN: SUCCESS (local auth) - User {user.id}")
                        flash(f'Welcome back! You have {user.get_remaining_analyses()} prompt improvements remaining.')
                        return redirect(url_for('home'))
                    else:
                        print(f"LOGIN: Password check FAILED")
                
                print(f"LOGIN: All authentication methods FAILED")
                flash('Invalid email or password.')
                return render_template('auth/login.html')
            
        except Exception as e:
            db.session.rollback()
            print(f"Login error: {e}")  # Debug logging
            flash('Error during login. Please try again.')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """Logout user - comprehensive session clearing"""
    print("LOGOUT: Route called")
    
    # Step 1: Try Supabase sign out (non-blocking)
    try:
        if current_user.is_authenticated and supabase_service:
            if hasattr(supabase_service, 'is_available') and supabase_service.is_available:
                if hasattr(current_user, 'supabase_id') and current_user.supabase_id:
                    supabase_service.sign_out()
                    print("LOGOUT: Supabase sign out completed")
    except Exception as e:
        print(f"LOGOUT: Supabase error (ignored): {e}")
    
    # Step 2: Flask-Login logout
    try:
        logout_user()
        print("LOGOUT: Flask-Login logout completed")
    except Exception as e:
        print(f"LOGOUT: Flask-Login error (ignored): {e}")
    
    # Step 3: Clear all session data
    try:
        # Clear individual session keys
        for key in list(session.keys()):
            session.pop(key, None)
        session.clear()
        session.modified = True
        print("LOGOUT: Session cleared")
    except Exception as e:
        print(f"LOGOUT: Session clear error (ignored): {e}")
    
    # Step 4: Create response and explicitly clear all cookies
    flash('You have been logged out of ColdMail.')
    print("LOGOUT: Redirecting to home")
    response = make_response(redirect(url_for('home')))
    
    # Clear the session cookie with all possible paths
    response.delete_cookie('session', path='/')
    response.delete_cookie('pitchai:session', path='/')
    
    # Clear Flask-Login's remember me cookie (CRITICAL for persistent sessions)
    response.delete_cookie('remember_token', path='/')
    
    # Force browser to delete cookies by setting expired values
    response.set_cookie('session', '', expires=0, max_age=0, path='/', httponly=True)
    response.set_cookie('remember_token', '', expires=0, max_age=0, path='/', httponly=True)
    
    print("LOGOUT: All cookies cleared, returning response")
    return response

@app.route('/session-debug')
def session_debug():
    """Debug session information"""
    debug_info = {
        'session_id': session.get('_id', 'No session ID'),
        'user_id': session.get('_user_id', 'No user ID'),
        'is_authenticated': current_user.is_authenticated,
        'current_user': str(current_user) if current_user.is_authenticated else 'Not logged in',
        'session_permanent': session.get('_permanent', False),
        'session_secure': app.config.get('SESSION_COOKIE_SECURE', 'Not set'),
        'session_httponly': app.config.get('SESSION_COOKIE_HTTPONLY', 'Not set'),
        'session_samesite': app.config.get('SESSION_COOKIE_SAMESITE', 'Not set'),
        'flask_env': os.environ.get('FLASK_ENV', 'Not set'),
        'secret_key_set': bool(app.config.get('SECRET_KEY')),
        'secret_key_length': len(app.config.get('SECRET_KEY', '')) if app.config.get('SECRET_KEY') else 0,
        'session_data': dict(session),
        'database_sessions': get_session_info()
    }
    return jsonify(debug_info)

@app.route('/db-sessions')
def db_sessions_debug():
    """Debug database sessions"""
    try:
        with app.app_context():
            # Get session info from Flask-Session
            session_info = get_session_info()
            
            return jsonify({
                'session_type': 'Flask-Session SQLAlchemy',
                'current_session_id': session.get('_id', 'No current session'),
                'session_info': session_info,
                'flask_session_config': {
                    'session_type': app.config.get('SESSION_TYPE'),
                    'session_table': app.config.get('SESSION_SQLALCHEMY_TABLE'),
                    'session_permanent': app.config.get('SESSION_PERMANENT'),
                    'session_lifetime': str(app.config.get('PERMANENT_SESSION_LIFETIME'))
                }
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cleanup-sessions')
def cleanup_sessions_route():
    """Clean up expired sessions via web route"""
    try:
        cleanup_expired_sessions()
        session_info = get_session_info()
        return jsonify({
            'status': 'success',
            'message': 'Session cleanup completed',
            'session_info': session_info
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/test-auth')
def test_auth():
    """Test authentication status"""
    if current_user.is_authenticated:
        return jsonify({
            'status': 'authenticated',
            'user_id': current_user.id,
            'email': current_user.email,
            'is_paid': current_user.is_paid,
            'remaining_analyses': current_user.get_remaining_analyses(),
            'supabase_id': getattr(current_user, 'supabase_id', None)
        })
    else:
        return jsonify({
            'status': 'not_authenticated',
            'message': 'No user is currently logged in',
            'session_data': dict(session),
            'flask_login_user': str(current_user)
        })

@app.route('/debug-login')
def debug_login():
    """Debug login information"""
    return jsonify({
        'current_user_authenticated': current_user.is_authenticated,
        'current_user_id': current_user.id if current_user.is_authenticated else None,
        'current_user_email': current_user.email if current_user.is_authenticated else None,
        'session_data': dict(session),
        'session_permanent': session.permanent,
        'flask_env': os.environ.get('FLASK_ENV', 'Not set'),
        'database_url': app.config['SQLALCHEMY_DATABASE_URI'],
        'supabase_configured': bool(os.environ.get('SUPABASE_URL')),
        'supabase_url': os.environ.get('SUPABASE_URL', 'Not set')[:20] + '...' if os.environ.get('SUPABASE_URL') else 'Not set'
    })

@app.route('/test-login')
def test_login_page():
    """Test login page for debugging"""
    return render_template('test_login.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Password reset request"""
    if request.method == 'POST':
        email = request.form.get('email')
        if email:
            result = supabase_service.reset_password(email)
            if result['success']:
                flash('Password reset email sent! Please check your inbox.')
            else:
                flash(f'Error: {result.get("error", "Failed to send reset email")}')
        else:
            flash('Please enter your email address.')
    
    return render_template('auth/reset_password.html')

@app.route('/verify-email')
def verify_email():
    """Email verification"""
    token = request.args.get('token')
    type = request.args.get('type', 'signup')
    
    if token:
        result = supabase_service.verify_email(token, type)
        if result:
            flash('Email verified successfully!')
            return redirect(url_for('login'))
        else:
            flash('Email verification failed. Please try again.')
    
    return redirect(url_for('login'))

@app.route('/upgrade')
@login_required
def upgrade():
    return render_template('upgrade.html')

@app.route('/paypal-checkout')
@login_required
def paypal_checkout():
    """Legacy route - redirects to upgrade page"""
    return redirect(url_for('upgrade'))

# --- Whop Webhook Integration ---
def verify_whop_signature(payload_bytes, headers):
    """Verify Whop webhook signature using the Standard Webhooks protocol."""
    secret = os.getenv('WHOP_WEBHOOK_SECRET')
    if not secret:
        print("Whop webhook: WHOP_WEBHOOK_SECRET is missing")
        return False

    msg_id = headers.get('webhook-id')
    timestamp = headers.get('webhook-timestamp')
    signature_header = headers.get('webhook-signature')

    if not all([msg_id, timestamp, signature_header]):
        print("Whop webhook: Missing signature headers")
        return False

    # Whop secrets may use whsec_ or ws_ prefix — strip either
    if secret.startswith('whsec_'):
        secret = secret[len('whsec_'):]
    elif secret.startswith('ws_'):
        secret = secret[len('ws_'):]

    try:
        secret_bytes = base64.b64decode(secret)
    except Exception:
        secret_bytes = secret.encode()

    # Reject stale webhooks (5 minute replay window)
    try:
        if abs(time.time() - int(timestamp)) > 300:
            print("Whop webhook: Timestamp outside replay window")
            return False
    except Exception:
        print("Whop webhook: Invalid timestamp header")
        return False

    signed_content = f"{msg_id}.{timestamp}.{payload_bytes.decode('utf-8', errors='replace')}"
    expected = base64.b64encode(
        hmac.new(secret_bytes, signed_content.encode('utf-8'), hashlib.sha256).digest()
    ).decode('utf-8')

    # The header can contain multiple signatures: "v1,<sig1> v1,<sig2>"
    for sig in signature_header.split(' '):
        parts = sig.split(',', 1)
        if len(parts) == 2 and parts[0] == 'v1':
            if hmac.compare_digest(expected, parts[1]):
                return True

    print("Whop webhook: Signature mismatch")
    return False


@app.route('/whop/webhook', methods=['POST'])
def whop_webhook():
    """Handle Whop payment webhook notifications with signature verification."""
    try:
        raw_payload = request.get_data()

        if not verify_whop_signature(raw_payload, request.headers):
            return jsonify({'success': False, 'message': 'Invalid signature'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data received'}), 400

        print(f"Whop webhook received: {data}")

        event_type = data.get('event') or data.get('action') or data.get('type')

        if event_type in ['membership.went_valid', 'payment.succeeded',
                          'membership_went_valid', 'payment_succeeded']:
            user_data = data.get('data', {})
            user_info = user_data.get('user', {}) or data.get('user', {})
            email = (user_info.get('email')
                     or user_data.get('email')
                     or data.get('email'))

            if email:
                user = User.query.filter_by(email=email).first()
                if user:
                    if not user.is_paid:
                        user.mark_paid()
                        send_payment_confirmation(user.email)
                        print(f"Whop webhook: User {email} upgraded to paid")
                    else:
                        print(f"Whop webhook: User {email} already paid")
                    return jsonify({'success': True, 'message': 'User upgraded'}), 200
                else:
                    print(f"Whop webhook: User {email} not found in database")
                    return jsonify({'success': False, 'message': 'User not found'}), 404
            else:
                print("Whop webhook: No email in webhook data")
                return jsonify({'success': False, 'message': 'No email provided'}), 400

        print(f"Whop webhook: Received event type: {event_type}")
        return jsonify({'success': True, 'message': 'Webhook received'}), 200

    except Exception as e:
        print(f"Whop webhook error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/whop/verify', methods=['POST'])
@login_required
def whop_verify_payment():
    """
    Manual verification endpoint - user can click to verify their Whop payment.
    This is a fallback if the webhook doesn't fire.
    """
    try:
        # For now, this is a manual verification that an admin would need to confirm
        # In production, you could integrate with Whop's API to verify membership
        flash('Payment verification requested. If you completed payment on Whop, your access will be activated shortly. Contact support if you need assistance.')
        return redirect(url_for('home'))
    except Exception as e:
        print(f"Whop verify error: {e}")
        flash('Error verifying payment. Please contact support.')
        return redirect(url_for('home'))

@app.route('/payment_success')
@login_required
def payment_success():
    """Legacy route - payment is now handled via Whop webhook"""
    flash('Payment processing. Your access will be activated shortly.')
    return redirect(url_for('home'))

# --- Simple Email Sender (prints to console for now) ---
def send_payment_confirmation(email):
    print(f"Payment confirmation sent to {email}")

# --- Session Management ---
def cleanup_expired_sessions():
    """Clean up expired sessions from database"""
    try:
        with app.app_context():
            # Flask-Session handles cleanup automatically, but we can add custom cleanup here if needed
            print("Session cleanup - Flask-Session handles this automatically")
    except Exception as e:
        print(f"Error in session cleanup: {e}")

def get_session_info():
    """Get current session information for debugging"""
    try:
        with app.app_context():
            # Flask-Session manages its own sessions, so we return basic info
            return {
                'session_type': 'Flask-Session SQLAlchemy',
                'session_table': 'sessions',
                'current_session_id': session.get('_id', 'No session ID'),
                'session_data': dict(session)
            }
    except Exception as e:
        return {'error': str(e)}

# --- Main App Routes ---
@app.route('/dark-mode-demo')
def dark_mode_demo():
    return render_template('dark-mode-demo.html')

@app.route('/')
def home():
    payment_success_param = request.args.get('payment') == 'success'

    if current_user.is_authenticated:
        remaining = current_user.get_remaining_analyses()

        if payment_success_param:
            flash('Payment successful! You now have Pro access (200/month).')

        return render_template('index.html',
                               remaining=remaining,
                               paid=current_user.is_paid,
                               models=IMAGE_VIDEO_MODELS)
    return render_template('index.html', remaining="6", paid=False, models=IMAGE_VIDEO_MODELS)

# --- AI App Builder Prompt Improver ---
def improve_prompt_with_ai(original_prompt):
    """Use AI to analyze and improve a prompt for AI app builders"""
    if not OPENAI_API_KEY:
        return None, None

    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }

    analysis_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are an expert at analyzing prompts for AI app builders (like Cursor, v0, Bolt, Lovable, Replit Agent). Analyze the given prompt and provide a brief analysis covering: 1) Clarity, 2) Technical Specificity, 3) Feature Details, 4) UI/UX Requirements. Keep your analysis concise - 2-3 sentences per point."},
            {"role": "user", "content": f"Analyze this AI app builder prompt:\n\n{original_prompt[:1500]}"}
        ],
        "max_tokens": 400,
        "temperature": 0.3
    }

    improvement_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are an expert at writing prompts for AI app builders (Cursor, v0, Bolt, Lovable, Replit Agent). Transform vague prompts into detailed, specific ones. Include: tech stack preferences, feature descriptions, UI/UX requirements, component structure, styling preferences. Output ONLY the improved prompt."},
            {"role": "user", "content": f"Improve this AI app builder prompt:\n\n{original_prompt[:1500]}"}
        ],
        "max_tokens": 800,
        "temperature": 0.4
    }

    analysis = None
    improved = None

    try:
        response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=analysis_data, timeout=15)
        response.raise_for_status()
        analysis = response.json()['choices'][0]['message']['content'].strip()

        response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=improvement_data, timeout=15)
        response.raise_for_status()
        improved = response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"AI prompt improvement error: {e}")

    return analysis, improved


def rule_based_prompt_analysis(prompt):
    """Analyze a prompt for AI app builders using rule-based checks"""
    analysis = {
        'word_count': len(prompt.split()),
        'char_count': len(prompt),
        'has_tech_stack': False,
        'has_feature_description': False,
        'has_ui_requirements': False,
        'has_functionality': False,
        'has_styling': False,
        'issues': [],
        'strengths': []
    }

    prompt_lower = prompt.lower()

    tech_patterns = [r'(react|vue|angular|svelte|next\.?js|nuxt|remix)', r'(tailwind|bootstrap|css|styled-components|chakra|material)', r'(node|express|flask|django|fastapi|rails)', r'(typescript|javascript|python|rust|go)', r'(postgres|mongodb|mysql|sqlite|supabase|firebase)', r'(api|rest|graphql|websocket)']
    for p in tech_patterns:
        if re.search(p, prompt_lower):
            analysis['has_tech_stack'] = True
            analysis['strengths'].append('Specifies tech stack or framework')
            break
    if not analysis['has_tech_stack']:
        analysis['issues'].append('No tech stack specified - consider adding preferred frameworks')

    feature_patterns = [r'(button|form|modal|navbar|sidebar|card|table|list|grid)', r'(login|signup|auth|dashboard|profile|settings|admin)', r'(search|filter|sort|pagination)', r'(upload|download|export|import|share)', r'(chart|graph|analytics|metrics|stats)']
    for p in feature_patterns:
        if re.search(p, prompt_lower):
            analysis['has_feature_description'] = True
            analysis['strengths'].append('Describes specific features or components')
            break
    if not analysis['has_feature_description']:
        analysis['issues'].append('Missing feature details - describe specific components you want')

    ui_patterns = [r'(responsive|mobile|desktop|tablet)', r'(dark mode|light mode|theme)', r'(layout|grid|flex|centered|sidebar)', r'(animation|transition|hover|smooth)', r'(modern|clean|minimal|professional|sleek)']
    for p in ui_patterns:
        if re.search(p, prompt_lower):
            analysis['has_ui_requirements'] = True
            analysis['strengths'].append('Includes UI/UX requirements')
            break
    if not analysis['has_ui_requirements']:
        analysis['issues'].append('No UI preferences - describe the look and feel you want')

    func_patterns = [r'(crud|create|read|update|delete)', r'(fetch|load|save|store|display)', r'(validate|check|verify|confirm)', r'(when|if|after|before|on click|on submit)', r'(user can|should be able to|allow|enable)']
    for p in func_patterns:
        if re.search(p, prompt_lower):
            analysis['has_functionality'] = True
            analysis['strengths'].append('Describes functionality and user actions')
            break
    if not analysis['has_functionality']:
        analysis['issues'].append('Missing functionality details - explain what users should be able to do')

    style_patterns = [r'(color|colours?|blue|green|red|purple|gradient)', r'(font|typography|text|heading)', r'(spacing|padding|margin|gap)', r'(border|rounded|shadow|blur)', r'(icon|image|logo|avatar)']
    for p in style_patterns:
        if re.search(p, prompt_lower):
            analysis['has_styling'] = True
            analysis['strengths'].append('Includes styling preferences')
            break
    if not analysis['has_styling']:
        analysis['issues'].append('No styling details - consider specifying colors, fonts, or visual style')

    score = 2
    if analysis['has_tech_stack']: score += 2
    if analysis['has_feature_description']: score += 2
    if analysis['has_ui_requirements']: score += 2
    if analysis['has_functionality']: score += 1
    if analysis['has_styling']: score += 1

    if analysis['word_count'] < 10:
        score -= 1
        analysis['issues'].append('Prompt is too short - AI builders work better with detailed prompts')
    elif analysis['word_count'] > 500:
        analysis['strengths'].append('Detailed prompt - good for complex apps')

    analysis['score'] = min(10, max(1, score))
    return analysis


# --- AI Image/Video Prompt Improver ---
def improve_image_prompt_with_ai(original_prompt, model_key):
    """Use AI to improve a prompt for image/video generation models"""
    if not OPENAI_API_KEY:
        return None, None

    model_name = IMAGE_VIDEO_MODELS.get(model_key, 'General')
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }

    model_tips = {
        'midjourney': "Use Midjourney-specific syntax: aspect ratios (--ar 16:9), style parameters (--s 750), quality (--q 2), version (--v 6). Use descriptive, comma-separated phrases. Midjourney responds well to artistic references, lighting descriptions, and camera angles.",
        'dalle3': "DALL-E 3 understands natural language well. Be very specific about composition, colors, lighting, and style. Mention if you want photorealistic, illustration, 3D render, etc. Avoid banned content terms.",
        'stable_diffusion': "Use weighted keywords with (parentheses) for emphasis. Include negative prompts. Specify style: photorealistic, anime, oil painting, etc. Mention technical details: 8k, detailed, masterpiece, best quality.",
        'veo': "Google Veo generates videos. Describe the scene, camera movement, lighting, mood, and temporal progression. Specify duration, transitions, and any text overlays needed for UGC content.",
        'runway': "Runway Gen-3 excels at video. Describe motion, camera angles, scene transitions. Be specific about subject movement, background changes, and visual effects.",
        'flux': "Flux excels at photorealistic images. Be specific about lighting (golden hour, studio, etc.), composition (rule of thirds, close-up), and subject details.",
        'leonardo': "Leonardo AI supports various styles. Specify the model/preset you want (PhotoReal, DreamShaper, etc.). Include negative prompts for better results.",
        'ideogram': "Ideogram is excellent at text in images. Clearly specify any text to include and its placement. Describe typography style, background, and overall composition.",
        'imagen': "Google Imagen (Nano Banana Pro) excels at photorealistic and artistic images. Be specific about scene composition, subject details, lighting, and artistic style. Supports natural language descriptions well. Mention quality keywords like high resolution, detailed, and specify aspect ratio if needed.",
    }

    tip = model_tips.get(model_key, "Be descriptive and specific about visual elements, style, composition, lighting, and mood.")

    analysis_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": f"You are an expert at analyzing prompts for AI image/video generation, specifically for {model_name}. Analyze the prompt for: 1) Visual Clarity - is the subject/scene clear? 2) Style Direction - does it specify artistic style? 3) Technical Details - resolution, aspect ratio, camera angle? 4) Composition - layout, lighting, mood? 5) UGC/Marketing Potential - is it suitable for product promotion or brand content? Keep analysis concise, 2-3 sentences per point."},
            {"role": "user", "content": f"Analyze this {model_name} prompt:\n\n{original_prompt[:1500]}"}
        ],
        "max_tokens": 400,
        "temperature": 0.3
    }

    improvement_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": f"You are an expert at writing prompts for {model_name} (AI image/video generation). {tip}\n\nYour job: take the user's basic prompt and transform it into an optimized, detailed prompt for {model_name} that will produce stunning results. If the content seems marketing/UGC-related, optimize for product promotion and brand awareness. Output ONLY the improved prompt, nothing else."},
            {"role": "user", "content": f"Improve this {model_name} prompt:\n\n{original_prompt[:1500]}"}
        ],
        "max_tokens": 600,
        "temperature": 0.4
    }

    analysis = None
    improved = None

    try:
        response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=analysis_data, timeout=15)
        response.raise_for_status()
        analysis = response.json()['choices'][0]['message']['content'].strip()

        response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=improvement_data, timeout=15)
        response.raise_for_status()
        improved = response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"AI image prompt improvement error: {e}")

    return analysis, improved


def rule_based_image_prompt_analysis(prompt, model_key):
    """Analyze an image/video prompt using rule-based checks"""
    model_name = IMAGE_VIDEO_MODELS.get(model_key, 'General')
    analysis = {
        'word_count': len(prompt.split()),
        'char_count': len(prompt),
        'has_subject': False,
        'has_style': False,
        'has_lighting': False,
        'has_composition': False,
        'has_mood': False,
        'model': model_name,
        'model_key': model_key,
        'issues': [],
        'strengths': []
    }

    prompt_lower = prompt.lower()

    subject_patterns = [r'(person|woman|man|child|animal|product|object|landscape|building|car|food)', r'(portrait|scene|background|foreground|character)', r'(wearing|holding|standing|sitting|running|flying)']
    for p in subject_patterns:
        if re.search(p, prompt_lower):
            analysis['has_subject'] = True
            analysis['strengths'].append('Clear subject description')
            break
    if not analysis['has_subject']:
        analysis['issues'].append('No clear subject - describe what should be in the image/video')

    style_patterns = [r'(photorealistic|realistic|cinematic|anime|cartoon|illustration|watercolor|oil painting)', r'(3d render|digital art|vector|flat design|minimalist|abstract)', r'(vintage|retro|futuristic|cyberpunk|fantasy|sci-fi)', r'(professional|studio|editorial|commercial|ugc|lifestyle)']
    for p in style_patterns:
        if re.search(p, prompt_lower):
            analysis['has_style'] = True
            analysis['strengths'].append('Specifies visual style')
            break
    if not analysis['has_style']:
        analysis['issues'].append('No style specified - add a visual style (cinematic, photorealistic, etc.)')

    lighting_patterns = [r'(lighting|light|lit|shadow|sunlight|golden hour|sunset|sunrise)', r'(bright|dark|moody|dramatic|soft|harsh|neon|glow)', r'(backlit|sidelit|rim light|ambient|studio light|natural light)']
    for p in lighting_patterns:
        if re.search(p, prompt_lower):
            analysis['has_lighting'] = True
            analysis['strengths'].append('Includes lighting details')
            break
    if not analysis['has_lighting']:
        analysis['issues'].append('No lighting details - specify lighting (golden hour, studio, dramatic, etc.)')

    comp_patterns = [r'(close-?up|wide shot|medium shot|aerial|bird.?s? eye|low angle|top down)', r'(centered|rule of thirds|symmetr|depth of field|bokeh|blur)', r'(aspect ratio|16:9|4:3|1:1|portrait|landscape|vertical|horizontal)', r'(camera|lens|zoom|macro|telephoto|fisheye)']
    for p in comp_patterns:
        if re.search(p, prompt_lower):
            analysis['has_composition'] = True
            analysis['strengths'].append('Describes composition or camera angle')
            break
    if not analysis['has_composition']:
        analysis['issues'].append('No composition details - add camera angle, framing, or aspect ratio')

    mood_patterns = [r'(mood|atmosphere|feel|vibe|tone|energy|emotion)', r'(happy|sad|mysterious|elegant|powerful|calm|energetic|bold)', r'(luxury|premium|playful|serious|warm|cool|cozy|epic)']
    for p in mood_patterns:
        if re.search(p, prompt_lower):
            analysis['has_mood'] = True
            analysis['strengths'].append('Sets the mood or atmosphere')
            break
    if not analysis['has_mood']:
        analysis['issues'].append('No mood/atmosphere - describe the feeling (bold, elegant, moody, etc.)')

    score = 2
    if analysis['has_subject']: score += 2
    if analysis['has_style']: score += 2
    if analysis['has_lighting']: score += 2
    if analysis['has_composition']: score += 1
    if analysis['has_mood']: score += 1

    if analysis['word_count'] < 5:
        score -= 1
        analysis['issues'].append('Prompt is very short - more detail produces better results')
    elif analysis['word_count'] > 100:
        analysis['strengths'].append('Detailed prompt - great for precise results')

    analysis['score'] = min(10, max(1, score))
    return analysis


# --- UGC Slideshow Image Generation ---

def analyze_product_image(image_bytes):
    """Use GPT-4o Vision to describe an uploaded product image."""
    if not OPENAI_API_KEY:
        return None

    b64_image = base64.b64encode(image_bytes).decode('utf-8')
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        "model": "gpt-4o",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Analyze this product image concisely. Describe: "
                        "1) Product type/category 2) Colors and materials "
                        "3) Any visible brand text or logo 4) Shape and proportions "
                        "5) Key visual features that make it recognizable. "
                        "Be specific — this description will be used to recreate "
                        "the product in AI-generated images."
                    )
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}
                }
            ]
        }],
        "max_tokens": 400,
        "temperature": 0.2
    }

    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers, json=data, timeout=30
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Product image analysis error: {e}")
        return None


def generate_ugc_scene_prompts(product_description, improved_prompt, num_scenes=4):
    """Generate diverse UGC-style scene descriptions using GPT-4o-mini."""
    if not OPENAI_API_KEY:
        return []

    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You generate UGC-style image prompts for product placement. "
                    "Each scene should feel authentic — like content a real creator "
                    "would post on TikTok or Instagram. NOT studio-perfect. Think: "
                    "handheld camera, natural lighting, real environments, casual framing. "
                    "Vary the settings (kitchen, desk, outdoor cafe, bathroom shelf, gym bag), "
                    "camera angles (selfie, overhead flat lay, close-up in hand, mirror shot), "
                    "and creator styles (clean girl, minimalist, cozy, energetic). "
                    "Each prompt must include the product description so the AI "
                    "generates the correct product. Return a JSON object with key "
                    "'scenes' containing an array of prompt strings."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Product description: {product_description}\n\n"
                    f"Style inspiration: {improved_prompt[:500]}\n\n"
                    f"Generate exactly {num_scenes} diverse UGC-style scene prompts. "
                    "Each should be a complete, detailed image generation prompt "
                    "(50-100 words) that places this specific product in an authentic "
                    "creator-style setting."
                )
            }
        ],
        "max_tokens": 1200,
        "temperature": 0.8,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers, json=data, timeout=25
        )
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content'].strip()
        parsed = json.loads(content)

        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    return v[:num_scenes]
        if isinstance(parsed, list):
            return parsed[:num_scenes]
        return []
    except Exception as e:
        print(f"UGC scene generation error: {e}")
        return []


def generate_image_imagen(prompt):
    """Generate an image using Google Imagen 3 via the Generative Language API."""
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not configured")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/imagen-3.0-generate-002:predict"
        f"?key={GOOGLE_API_KEY}"
    )
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "1:1",
            "safetyFilterLevel": "block_only_high",
            "personGeneration": "allow_adult"
        }
    }

    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()
    result = response.json()

    predictions = result.get('predictions', [])
    if not predictions:
        raise ValueError("No image returned from Google Imagen")

    image_b64 = predictions[0].get('bytesBase64Encoded')
    if not image_b64:
        raise ValueError("No image data in Google Imagen response")

    return base64.b64decode(image_b64)


def generate_slideshow_images(scene_prompts, provider):
    """Generate multiple images in parallel for a UGC slideshow."""
    gen_func = generate_image_imagen
    results = [None] * len(scene_prompts)
    errors = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for i, prompt in enumerate(scene_prompts):
            futures[executor.submit(gen_func, prompt)] = i

        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                print(f"Image generation error (scene {idx}): {e}")
                errors.append(str(e))
                results[idx] = None

    return results, errors


# --- Routes: App Builder Prompt ---
@app.route('/improve-prompt', methods=['POST'])
@login_required
def improve_prompt():
    if not current_user.can_analyze():
        if current_user.is_paid:
            flash('Monthly limit reached (200/month). Resets next month.')
            return redirect(url_for('home'))
        else:
            flash('Free tier limit reached. Upgrade for 200 prompts per month!')
            return redirect(url_for('upgrade'))

    prompt_content = request.form.get('prompt_content', '')
    if not prompt_content.strip():
        flash('Please enter a prompt to improve.')
        return redirect(url_for('home'))

    rule_analysis = rule_based_prompt_analysis(prompt_content)
    ai_analysis, improved_prompt = improve_prompt_with_ai(prompt_content)

    session['prompt_result'] = {
        'original_prompt': prompt_content,
        'improved_prompt': improved_prompt or '(Could not generate improved prompt. Please try again.)',
        'ai_analysis': ai_analysis,
        'rule_analysis': rule_analysis,
        'tool_type': 'app_builder'
    }

    current_user.increment_analysis()
    return redirect(url_for('prompt_result'))


# --- Routes: Image/Video Prompt ---
@app.route('/improve-image-prompt', methods=['POST'])
@login_required
def improve_image_prompt():
    if not current_user.can_analyze():
        if current_user.is_paid:
            flash('Monthly limit reached (200/month). Resets next month.')
            return redirect(url_for('home'))
        else:
            flash('Free tier limit reached. Upgrade for 200 prompts per month!')
            return redirect(url_for('upgrade'))

    prompt_content = request.form.get('prompt_content', '')
    model_key = request.form.get('model', 'midjourney')

    if not prompt_content.strip():
        flash('Please enter a prompt to improve.')
        return redirect(url_for('home'))

    if model_key not in IMAGE_VIDEO_MODELS:
        model_key = 'midjourney'

    rule_analysis = rule_based_image_prompt_analysis(prompt_content, model_key)
    ai_analysis, improved_prompt = improve_image_prompt_with_ai(prompt_content, model_key)

    session['prompt_result'] = {
        'original_prompt': prompt_content,
        'improved_prompt': improved_prompt or '(Could not generate improved prompt. Please try again.)',
        'ai_analysis': ai_analysis,
        'rule_analysis': rule_analysis,
        'tool_type': 'image_video',
        'model': IMAGE_VIDEO_MODELS.get(model_key, 'General'),
        'model_key': model_key
    }

    current_user.increment_analysis()
    return redirect(url_for('prompt_result'))


@app.route('/generate-slideshow', methods=['POST'])
@login_required
def generate_slideshow():
    if not current_user.can_generate_slideshow():
        if current_user.is_paid:
            flash('Monthly slideshow limit reached (50/month). Resets next month.')
        else:
            flash('Free slideshow limit reached (1/month). Upgrade for 50 per month!')
            return redirect(url_for('upgrade'))
        return redirect(url_for('prompt_result'))

    prompt_data = session.get('prompt_result', {})
    if not prompt_data:
        flash('Please optimize a prompt first.')
        return redirect(url_for('home'))

    improved_prompt = prompt_data.get('improved_prompt', '')
    provider = request.form.get('provider', 'imagen')

    if provider != 'imagen':
        flash('Invalid provider selected.')
        return redirect(url_for('prompt_result'))

    if 'product_image' not in request.files:
        flash('Please upload a product image.')
        return redirect(url_for('prompt_result'))

    file = request.files['product_image']
    if file.filename == '':
        flash('No file selected.')
        return redirect(url_for('prompt_result'))

    image_bytes = file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        flash('Image too large. Please upload an image under 10MB.')
        return redirect(url_for('prompt_result'))

    product_description = analyze_product_image(image_bytes)
    if not product_description:
        flash('Could not analyze the product image. Please try again.')
        return redirect(url_for('prompt_result'))

    scene_prompts = generate_ugc_scene_prompts(product_description, improved_prompt, num_scenes=4)
    if not scene_prompts:
        flash('Could not generate scene descriptions. Please try again.')
        return redirect(url_for('prompt_result'))

    image_bytes_list, errors = generate_slideshow_images(scene_prompts, provider)

    batch_id = str(uuid.uuid4())[:12]
    batch_dir = os.path.join(GENERATED_DIR, batch_id)
    os.makedirs(batch_dir, exist_ok=True)

    image_urls = []
    for i, img_bytes in enumerate(image_bytes_list):
        if img_bytes:
            filename = f"scene_{i}.png"
            filepath = os.path.join(batch_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(img_bytes)
            image_urls.append(f"/static/generated/{batch_id}/{filename}")

    if not image_urls:
        flash('Image generation failed. Please check your API configuration and try again.')
        if errors:
            print(f"Slideshow generation errors: {errors}")
        return redirect(url_for('prompt_result'))

    current_user.increment_slideshow_generation()

    session['slideshow_result'] = {
        'images': image_urls,
        'scene_prompts': scene_prompts,
        'product_description': product_description,
        'provider': 'Google Nano Banana/Imagen',
        'provider_key': provider,
        'batch_id': batch_id,
        'original_prompt': prompt_data.get('original_prompt', ''),
        'improved_prompt': improved_prompt,
        'num_generated': len(image_urls),
        'num_failed': len(scene_prompts) - len(image_urls)
    }

    return redirect(url_for('slideshow_result'))


@app.route('/slideshow-result')
@login_required
def slideshow_result():
    slideshow_data = session.get('slideshow_result', {})
    if not slideshow_data:
        return redirect(url_for('home'))

    try:
        remaining = current_user.get_remaining_slideshows()
    except Exception:
        remaining = 0

    return render_template('slideshow_result.html',
                         slideshow_data=slideshow_data,
                         paid=current_user.is_paid,
                         remaining_slideshows=remaining)


@app.route('/prompt-result')
@login_required
def prompt_result():
    prompt_data = session.get('prompt_result', {})

    if not prompt_data:
        return redirect(url_for('home'))

    try:
        remaining = current_user.get_remaining_slideshows()
    except Exception:
        remaining = 0

    return render_template('prompt_result.html',
                         prompt_data=prompt_data,
                         paid=current_user.is_paid,
                         remaining_slideshows=remaining)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/health')
def health_check():
    try:
        # Test database connection
        db_status = "healthy"
        try:
            with app.app_context():
                try:
                    # Try newer SQLAlchemy syntax first
                    with db.engine.connect() as connection:
                        result = connection.execute(db.text('SELECT 1'))
                        result.close()
                except AttributeError:
                    # Fall back to older SQLAlchemy syntax
                    result = db.engine.execute('SELECT 1')
                    result.close()
        except Exception as db_error:
            db_status = f"error: {str(db_error)}"
        
        # Check environment variables
        env_vars = {
            'FLASK_SECRET_KEY': bool(os.environ.get('FLASK_SECRET_KEY')),
            'OPENAI_API_KEY': bool(os.environ.get('OPENAI_API_KEY')),
            'DATABASE_URL': bool(os.environ.get('DATABASE_URL'))
        }
        
        return jsonify({
            "status": "healthy" if db_status == "healthy" else "degraded", 
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_status,
            "environment_variables": env_vars,
            "database_url": app.config['SQLALCHEMY_DATABASE_URI'],
            "debug_mode": app.debug,
            "session_config": {
                "secure": app.config.get('SESSION_COOKIE_SECURE', False),
                "httponly": app.config.get('SESSION_COOKIE_HTTPONLY', True),
                "samesite": app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/init-db')
def init_db_route():
    """Initialize database via web route (for debugging)"""
    try:
        with app.app_context():
            db.create_all()
        return jsonify({"status": "success", "message": "Database initialized successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "type": type(e).__name__}), 500

@app.route('/test-db')
def test_db():
    """Test database connection"""
    try:
        with app.app_context():
            # Test basic connection
            try:
                # Try newer SQLAlchemy syntax first
                with db.engine.connect() as connection:
                    result = connection.execute(db.text('SELECT 1 as test')).fetchone()
            except AttributeError:
                # Fall back to older SQLAlchemy syntax
                result = db.engine.execute('SELECT 1 as test').fetchone()
            
            return jsonify({
                "status": "success", 
                "message": "Database connection working",
                "test_result": result[0] if result else None,
                "database_url": app.config['SQLALCHEMY_DATABASE_URI']
            })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e), 
            "type": type(e).__name__,
            "database_url": app.config['SQLALCHEMY_DATABASE_URI']
        }), 500

@app.route('/server-info')
def server_info():
    """Get server information for debugging"""
    import platform
    import sys
    
    try:
        return jsonify({
            "python_version": sys.version,
            "platform": platform.platform(),
            "app_name": app.name,
            "app_debug": app.debug,
            "app_testing": app.testing,
            "environment": os.environ.get('FLASK_ENV', 'production'),
            "port": os.environ.get('PORT', '5000'),
            "database_url": app.config['SQLALCHEMY_DATABASE_URI'],
            "secret_key_set": bool(app.config['SECRET_KEY']),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/check-db')
def check_db():
    """Check database status and initialize if needed"""
    try:
        with app.app_context():
            # Test connection
            try:
                # Try newer SQLAlchemy syntax first
                with db.engine.connect() as connection:
                    result = connection.execute(db.text('SELECT 1'))
                    result.close()
            except AttributeError:
                # Fall back to older SQLAlchemy syntax
                result = db.engine.execute('SELECT 1')
                result.close()
            
            # Check if User table exists
            try:
                user_count = User.query.count()
                return jsonify({
                    "status": "success",
                    "message": "Database is working",
                    "user_count": user_count,
                    "database_url": app.config['SQLALCHEMY_DATABASE_URI']
                })
            except Exception as table_error:
                # Table doesn't exist, create it
                db.create_all()
                return jsonify({
                    "status": "success",
                    "message": "Database initialized",
                    "user_count": 0,
                    "database_url": app.config['SQLALCHEMY_DATABASE_URI']
                })
                
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "database_url": app.config['SQLALCHEMY_DATABASE_URI']
        }), 500

@app.route('/deployment-status')
def deployment_status():
    """Check deployment status and configuration"""
    try:
        with app.app_context():
            # Test database
            db_status = "working"
            user_count = 0
            try:
                user_count = User.query.count()
            except Exception as e:
                db_status = f"error: {str(e)}"
            
            return jsonify({
                "status": "deployed",
                "timestamp": datetime.utcnow().isoformat(),
                "database": {
                    "status": db_status,
                    "url": app.config['SQLALCHEMY_DATABASE_URI'],
                    "user_count": user_count
                },
                "environment": {
                    "flask_secret_key_set": bool(app.config['SECRET_KEY']),
                    "openai_api_key_set": bool(os.environ.get('OPENAI_API_KEY')),
                    "database_url_set": bool(os.environ.get('DATABASE_URL'))
                },
                "app_config": {
                    "debug": app.debug,
                    "testing": app.testing,
                    "secret_key_length": len(app.config['SECRET_KEY']) if app.config['SECRET_KEY'] else 0
                }
            })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

# --- Database initialization ---
@app.cli.command("init-db")
def init_db():
    """Initialize the database."""
    db.create_all()
    print('Initialized the database.')

def init_database():
    """Initialize the database with proper error handling"""
    print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Environment DATABASE_URL: {os.environ.get('DATABASE_URL', 'Not set')}")
    
    try:
        with app.app_context():
            # Test database connection first
            try:
                # Try newer SQLAlchemy syntax first
                with db.engine.connect() as connection:
                    result = connection.execute(db.text('SELECT 1'))
                    result.close()
            except AttributeError:
                # Fall back to older SQLAlchemy syntax
                result = db.engine.execute('SELECT 1')
                result.close()
            print('Database connection successful')
            
            # Create tables (including sessions table)
            db.create_all()
            print('Database initialized successfully')
            
            # Verify sessions table was created
            try:
                # Check if sessions table exists
                with db.engine.connect() as connection:
                    result = connection.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"))
                    sessions_exists = result.fetchone()
                    if sessions_exists:
                        print('✓ Sessions table created successfully')
                    else:
                        print('⚠ Sessions table not found, creating manually...')
                        # Create sessions table manually if needed
                        db.create_all()
            except Exception as table_check_error:
                print(f'Could not verify sessions table: {table_check_error}')
            
            # Check if tables exist
            try:
                tables = db.engine.table_names()
                print(f'Available tables: {tables}')
            except Exception as table_error:
                print(f'Could not list tables: {table_error}')
                
    except Exception as e:
        print(f'Error initializing database: {e}')
        print(f'Error type: {type(e).__name__}')
        
        # Try alternative approach for SQLite
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            try:
                with app.app_context():
                    # Ensure the instance directory exists
                    import os
                    instance_path = os.path.join(os.getcwd(), 'instance')
                    if not os.path.exists(instance_path):
                        os.makedirs(instance_path)
                        print(f'Created instance directory: {instance_path}')
                    
                    db.create_all()
                    print('Database tables created successfully (SQLite retry)')
            except Exception as e2:
                print(f'Failed to create database tables: {e2}')
                print(f'Second error type: {type(e2).__name__}')
        else:
            # For other databases, try one more time
            try:
                with app.app_context():
                    db.create_all()
                    print('Database tables created successfully (retry)')
            except Exception as e2:
                print(f'Failed to create database tables: {e2}')
                print(f'Second error type: {type(e2).__name__}')

if __name__ == '__main__':
    try:
        print("Starting PitchAI application...")
        init_database()
        
        # Clean up expired sessions on startup
        cleanup_expired_sessions()
        
        # Get port from environment variable (for deployment) or use 5000 for local development
        port = int(os.environ.get('PORT', 5000))
        print(f"Starting server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=True)  # Enable debug mode to see errors
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc() 