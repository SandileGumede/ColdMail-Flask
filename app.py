from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User
import re
import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import paypalrestsdk
import time

load_dotenv()
import os
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
print('OPENAI_API_KEY loaded:', OPENAI_API_KEY)

PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET')

paypalrestsdk.configure({
    "mode": "live",  # Change to "live" for production
    "client_id": PAYPAL_CLIENT_ID or "AbgwSoNkogaIZ6yw4zyYw1xIHJJ7wornxDyqrcmiadv8G5_W_zhlz-Z2K5krNiOBvg7TkUUFHmq0PxYe",
    "client_secret": PAYPAL_CLIENT_SECRET or "EPMJhQwyzkPD6qAvjhR0eT8SReJs0db8stTISWinxkKFWVDoNEs4wq0wFK5QB7owXy6Tx_hMqN_I3xeM"
})

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Session configuration
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

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

# Use environment variable for database URL (for production) or default to SQLite
database_url = os.environ.get('DATABASE_URL')
if not database_url:
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

# Initialize database on startup
if not ensure_db_initialized():
    print("Warning: Database initialization failed, but continuing startup...")

# --- Main Application Routes ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

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
def rule_based_spam_score(email_content):
    spam_triggers = [
        r'limited time', r'click here', r'buy now', r'act now', r'exclusive offer', r'free money',
        r'make money fast', r'earn cash', r'guaranteed', r'no risk', r'urgent', r'limited offer',
        r'once in a lifetime', r"don't miss out", r'last chance'
    ]
    spam_words_found = []
    score = 1  # Start at 1 for baseline
    for pattern in spam_triggers:
        if re.search(pattern, email_content, re.IGNORECASE):
            spam_words_found.append(pattern)
            score += 1
    # Pushiness: exclamation marks, ALL CAPS words
    exclamations = email_content.count('!')
    all_caps = len(re.findall(r'\b[A-Z]{3,}\b', email_content))
    score += min(exclamations, 3)  # Cap at 3
    score += min(all_caps, 2)      # Cap at 2
    return min(score, 10), spam_words_found, exclamations, all_caps

def rule_based_personalization(email_content):
    has_name = '{Name}' in email_content or '{name}' in email_content
    has_company = '{Company}' in email_content or '{company}' in email_content
    return has_name or has_company, has_name, has_company

def rule_based_subject_grade(subject):
    length = len(subject)
    is_question = subject.strip().endswith('?')
    if 30 <= length <= 50:
        grade = 'A' if is_question else 'B'
    elif 20 <= length < 30 or 50 < length <= 60:
        grade = 'B' if is_question else 'C'
    else:
        grade = 'C' if is_question else 'D'
    return grade, length, is_question

def call_openai(prompt):
    if not OPENAI_API_KEY:
        return None
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 30,
        "temperature": 0.2
    }
    try:
        response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        return None

# --- Main Analysis Logic ---
def analyze_email(email_content):
    # Accepts cold DM or cold email content
    lines = email_content.strip().split('\n')
    subject = lines[0] if lines else ''
    body = '\n'.join(lines[1:]) if len(lines) > 1 else ''

    # 1. Spam Shield
    spam_score, spam_words_found, exclamations, all_caps = rule_based_spam_score(email_content)

    # 2. Personalization Checker (Rule + ChatGPT)
    has_personalization, has_name, has_company = rule_based_personalization(email_content)
    personalization_gpt = None
    if current_user.can_analyze():
        prompt = f"Does this email feel personalized? Reply YES or NO. Email: {email_content[:1000]}"
        gpt_response = call_openai(prompt)
        if gpt_response:
            personalization_gpt = 'YES' in gpt_response.upper()
    else:
        personalization_gpt = None

    personalization_final = has_personalization or (personalization_gpt is True)

    # 3. Subject Line Grader
    subject_grade, subject_length, is_question = rule_based_subject_grade(subject)

    # 4. Structure Doctor (ChatGPT)
    structure_suggestion = None
    if current_user.can_analyze():
        prompt = f"Suggest 1 short improvement for clarity in this email. Email: {email_content[:1000]}"
        gpt_response = call_openai(prompt)
        if gpt_response:
            structure_suggestion = gpt_response

    # 5. Improved Cold DM/Email (ChatGPT)
    improved_message = None
    if current_user.can_analyze():
        prompt = (
            "Rewrite this cold DM or cold email to improve clarity, personalization, and reduce spamminess. "
            "Keep it concise and professional. Only output the improved message.\n\n" + email_content[:1000]
        )
        gpt_response = call_openai(prompt)
        if gpt_response:
            improved_message = gpt_response.strip()
    # Fallback if no improvement
    if not improved_message:
        improved_message = "(Could not generate improved cold DM/email. Try again or check your input.)"

    # --- Merge outputs (Anti-Wrapper) ---
    merged_personalization = 'YES' if personalization_final else 'NO'
    merged_structure = structure_suggestion or (
        "Try to personalize your email and keep it concise." if not personalization_final else "Looks clear!"
    )
    # Compose overall score (Spam + Personalization + Subject)
    # Old: lower score = better, higher = worse
    # New: higher score = better, lower = worse
    # We'll use a 10-point scale, where 10 is best, 1 is worst
    # Start from 10, subtract for each issue
    score = 10
    score -= spam_score - 1  # spam_score: 1 (best) to 10 (worst), so subtract (spam_score-1)
    if not personalization_final:
        score -= 2
    if subject_grade not in ['A','B']:
        score -= 1
    overall_score = max(1, min(10, score))

    return {
        'spam_words_found': spam_words_found,
        'spam_score': spam_score,
        'exclamations': exclamations,
        'all_caps': all_caps,
        'personalization': merged_personalization,
        'has_name': has_name,
        'has_company': has_company,
        'subject': subject,
        'subject_length': subject_length,
        'subject_grade': subject_grade,
        'is_question': is_question,
        'structure_suggestion': merged_structure,
        'overall_score': overall_score,
        'improved_message': improved_message
    }

# --- Authentication Routes ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            print(f"Signup attempt for email: {email}")  # Debug logging
            
            # Validate input
            if not email or not password:
                flash('Please fill in all fields.')
                return render_template('auth/signup.html')
            
            if password != confirm_password:
                flash('Passwords do not match.')
                return render_template('auth/signup.html')
            
            if len(password) < 6:
                flash('Password must be at least 6 characters long.')
                return render_template('auth/signup.html')
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email already registered. Please login.')
                return redirect(url_for('login'))
            
            # Create new user
            user = User()
            user.email = email
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            print(f"User created successfully: {user.id}")  # Debug logging
            
            login_user(user, remember=True)
            flash('Account created successfully! You have 3 free ColdMail analyses.')
            return redirect(url_for('home'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Signup error: {e}")  # Debug logging
            flash('Error creating account. Please try again.')
            return render_template('auth/signup.html')
    
    return render_template('auth/signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            remember = request.form.get('remember') == 'on'
            
            print(f"Login attempt for email: {email}")  # Debug logging
            
            # Validate input
            if not email or not password:
                flash('Please fill in all fields.')
                return render_template('auth/login.html')
            
            # Check if user exists
            user = User.query.filter_by(email=email).first()
            if not user:
                print(f"Login failed: User not found for email: {email}")
                flash('Invalid email or password.')
                return render_template('auth/login.html')
            
            # Check password
            if not user.check_password(password):
                print(f"Login failed: Invalid password for email: {email}")
                flash('Invalid email or password.')
                return render_template('auth/login.html')
            
            # Login successful
            login_user(user, remember=remember)
            
            # Set session as permanent if remember is checked
            if remember:
                session.permanent = True
            
            # Update user last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            print(f"User logged in successfully: {user.id}")  # Debug logging
            print(f"Session ID: {session.sid if hasattr(session, 'sid') else 'No session ID'}")
            print(f"User authenticated: {current_user.is_authenticated}")
            
            flash(f'Welcome back! You have {user.get_remaining_analyses()} ColdMail analyses remaining.')
            return redirect(url_for('home'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Login error: {e}")  # Debug logging
            flash('Error during login. Please try again.')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out of ColdMail.')
    return redirect(url_for('home'))

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
        'secret_key_length': len(app.config.get('SECRET_KEY', '')) if app.config.get('SECRET_KEY') else 0
    }
    return jsonify(debug_info)

@app.route('/test-auth')
def test_auth():
    """Test authentication status"""
    if current_user.is_authenticated:
        return jsonify({
            'status': 'authenticated',
            'user_id': current_user.id,
            'email': current_user.email,
            'is_paid': current_user.is_paid,
            'remaining_analyses': current_user.get_remaining_analyses()
        })
    else:
        return jsonify({
            'status': 'not_authenticated',
            'message': 'No user is currently logged in'
        })

@app.route('/test-login')
def test_login_page():
    """Test login page for debugging"""
    return render_template('test_login.html')

@app.route('/upgrade')
@login_required
def upgrade():
    return render_template('paypal_checkout.html', paypal_client_id=PAYPAL_CLIENT_ID)

@app.route('/paypal-checkout')
@login_required
def paypal_checkout():
    """Direct PayPal checkout page"""
    return render_template('paypal_checkout.html', paypal_client_id=PAYPAL_CLIENT_ID)

@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": url_for('payment_success', _external=True),
            "cancel_url": url_for('upgrade', _external=True)
        },
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": "PitchAI Unlimited Analyses",
                    "sku": "001",
                    "price": "20.00",
                    "currency": "USD",
                    "quantity": 1
                }]
            },
            "amount": {
                "total": "20.00",
                "currency": "USD"
            },
            "description": "Unlimited analyses upgrade for PitchAI."
        }]
    })
    if payment.create():
        for link in payment.links:
            if link.rel == "approval_url":
                approval_url = str(link.href)
                return redirect(approval_url)
        flash('Payment created but approval URL not found.')
        return redirect(url_for('upgrade'))
    else:
        flash('Error creating PayPal payment: ' + payment.error.get('message', 'Unknown error'))
        return redirect(url_for('upgrade'))

@app.route('/api/orders', methods=['POST'])
@login_required
def create_paypal_order():
    """Create a PayPal order on the server side"""
    try:
        # Create PayPal order using the SDK
        order = paypalrestsdk.Order({
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": "20.00"
                },
                "description": "PitchAI Unlimited Analyses Upgrade",
                "custom_id": f"user_{current_user.id}_upgrade"
            }],
            "application_context": {
                "return_url": url_for('payment_success', _external=True),
                "cancel_url": url_for('upgrade', _external=True)
            }
        })
        
        if order.create():
            return jsonify({
                "id": order.id,
                "status": order.status
            })
        else:
            error_message = order.error.get('message', 'Unknown error')
            return jsonify({
                "error": error_message,
                "debug_id": order.error.get('debug_id', 'No debug ID')
            }), 400
            
    except Exception as e:
        print(f"Error creating PayPal order: {e}")
        return jsonify({
            "error": "Internal server error",
            "debug_id": "server_error"
        }), 500

@app.route('/api/orders/<order_id>/capture', methods=['POST'])
@login_required
def capture_paypal_order(order_id):
    """Capture a PayPal order and upgrade user account"""
    try:
        # Find the order
        order = paypalrestsdk.Order.find(order_id)
        
        if not order:
            return jsonify({
                "error": "Order not found",
                "debug_id": "order_not_found"
            }), 404
        
        # Capture the order
        if order.capture():
            # Check if capture was successful
            if order.status == "COMPLETED":
                # Mark user as paid
                current_user.mark_paid()
                db.session.commit()
                
                # Send confirmation email
                send_payment_confirmation(current_user.email)
                
                return jsonify({
                    "id": order.id,
                    "status": order.status,
                    "purchase_units": order.purchase_units
                })
            else:
                return jsonify({
                    "error": f"Order not completed. Status: {order.status}",
                    "debug_id": "incomplete_order"
                }), 400
        else:
            error_message = order.error.get('message', 'Unknown error')
            return jsonify({
                "error": error_message,
                "debug_id": order.error.get('debug_id', 'No debug ID')
            }), 400
            
    except Exception as e:
        print(f"Error capturing PayPal order: {e}")
        return jsonify({
            "error": "Internal server error",
            "debug_id": "server_error"
        }), 500

@app.route('/paypal_webhook', methods=['POST'])
@login_required
def paypal_webhook():
    """Handle PayPal payment webhook from frontend (legacy support)"""
    try:
        data = request.get_json()
        order_id = data.get('orderID')
        payer_id = data.get('payerID')
        payment_details = data.get('paymentDetails')
        
        if not all([order_id, payer_id, payment_details]):
            return jsonify({'success': False, 'message': 'Missing payment information'}), 400
        
        # Verify payment status
        if payment_details.get('status') == 'COMPLETED':
            # Mark user as paid
            current_user.mark_paid()
            db.session.commit()
            
            # Send confirmation email
            send_payment_confirmation(current_user.email)
            
            return jsonify({
                'success': True, 
                'message': 'Payment verified successfully',
                'order_id': order_id
            })
        else:
            return jsonify({'success': False, 'message': 'Payment not completed'}), 400
            
    except Exception as e:
        print(f"PayPal webhook error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/payment_success')
@login_required
def payment_success():
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    payment = paypalrestsdk.Payment.find(payment_id)
    if payment.execute({"payer_id": payer_id}):
        current_user.mark_paid()
        send_payment_confirmation(current_user.email)
        flash('Payment successful! Unlimited analyses unlocked.')
        return redirect(url_for('home'))
    else:
        flash('Payment execution failed: ' + payment.error.get('message', 'Unknown error'))
        return redirect(url_for('upgrade'))

# --- Simple Email Sender (prints to console for now) ---
def send_payment_confirmation(email):
    print(f"Payment confirmation sent to {email}")

# --- Main App Routes ---
@app.route('/')
def home():
    if current_user.is_authenticated:
        remaining = current_user.get_remaining_analyses()
        print(f"User {current_user.email} is authenticated, remaining analyses: {remaining}")
        return render_template('index.html', remaining=remaining, paid=current_user.is_paid)
    else:
        print("No user is currently authenticated")
    return render_template('index.html', remaining="3", paid=False)

@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    if not current_user.can_analyze():
        flash('Free tier limit reached. Please upgrade for unlimited analyses!')
        return redirect(url_for('upgrade'))
    
    email_content = request.form.get('email_content', '')
    if not email_content.strip():
        flash('Please enter your cold DM or cold email content.')
        return redirect(url_for('home'))
    
    # Analyze the cold DM or cold email
    analysis_result = analyze_email(email_content)
    
    # Store results in session
    session['analysis_result'] = analysis_result
    session['email_content'] = email_content
    
    # Increment analysis count for free users
    current_user.increment_analysis()
    
    return redirect(url_for('result'))

@app.route('/result')
@login_required
def result():
    analysis_result = session.get('analysis_result', {})
    email_content = session.get('email_content', '')
    
    if not analysis_result:
        return redirect(url_for('home'))
    
    return render_template('result.html', 
                         analysis=analysis_result, 
                         email_content=email_content,
                         paid=current_user.is_paid)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

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
            'PAYPAL_CLIENT_ID': bool(os.environ.get('PAYPAL_CLIENT_ID')),
            'PAYPAL_CLIENT_SECRET': bool(os.environ.get('PAYPAL_CLIENT_SECRET')),
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
                    "paypal_client_id_set": bool(os.environ.get('PAYPAL_CLIENT_ID')),
                    "paypal_client_secret_set": bool(os.environ.get('PAYPAL_CLIENT_SECRET')),
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
            
            # Create tables
            db.create_all()
            print('Database initialized successfully')
            
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
    init_database()
    # Get port from environment variable (for deployment) or use 5000 for local development
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 