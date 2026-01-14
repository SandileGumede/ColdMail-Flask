from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_session import Session
from models import db, User
from supabase_service import SupabaseService
import re
import os 
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import paypalrestsdk
import time
import json

load_dotenv()
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print("OPENAI_API_KEY loaded:", OPENAI_API_KEY is not None)

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")

paypalrestsdk.configure({
    "mode": "live",  # Change to "live" for production
    "client_id": PAYPAL_CLIENT_ID ,
    "client_secret": PAYPAL_CLIENT_SECRET
})

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

# Initialize database on startup
if not ensure_db_initialized():
    print("Warning: Database initialization failed, but continuing startup...")

# Initialize Flask-Session after database is configured
Session(app)

# --- Main Application Routes ---
@app.route("/login/process", methods=["GET", "POST"])
def user_login():
    
    if request.method == "GET":
        return render_template("login.html")
    
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            session['user_id'] = user.id
            session.permanent = True
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password")
            
    return render_template("login.html")

@app.route("/signup/process", methods=["GET", "POST"])
def signup_user():
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
    """
    Advanced personalization scoring with multiple indicators.
    Returns: score (0-10), details dict
    """
    content_lower = email_content.lower()
    details = {
        'has_name_placeholder': False,
        'has_company_placeholder': False,
        'has_role_reference': False,
        'has_specific_reference': False,
        'has_custom_opening': False,
        'has_mutual_connection': False,
        'has_recent_trigger': False,
        'indicators_found': []
    }
    score = 0
    
    # 1. Name placeholders (various formats) - 2 points
    name_patterns = [
        r'\{name\}', r'\{first_name\}', r'\{firstname\}', r'\[name\]', 
        r'\[first_name\]', r'\{\{name\}\}', r'<<name>>'
    ]
    for pattern in name_patterns:
        if re.search(pattern, content_lower):
            details['has_name_placeholder'] = True
            details['indicators_found'].append('Name placeholder')
            score += 2
            break
    
    # 2. Company placeholders - 2 points
    company_patterns = [
        r'\{company\}', r'\{company_name\}', r'\[company\]', 
        r'\{\{company\}\}', r'<<company>>'
    ]
    for pattern in company_patterns:
        if re.search(pattern, content_lower):
            details['has_company_placeholder'] = True
            details['indicators_found'].append('Company placeholder')
            score += 2
            break
    
    # 3. Role/title references - 1 point
    role_patterns = [
        r'\b(your role as|in your position|as a |as an |your work as)\b',
        r'\{role\}', r'\{title\}', r'\{job_title\}',
        r'\b(ceo|cto|cfo|founder|director|manager|head of|vp of|lead)\b'
    ]
    for pattern in role_patterns:
        if re.search(pattern, content_lower):
            details['has_role_reference'] = True
            details['indicators_found'].append('Role/title reference')
            score += 1
            break
    
    # 4. Specific references (shows research) - 2 points
    specific_patterns = [
        r'\b(i saw your|i read your|i noticed your|your recent|your latest)\b',
        r'\b(your post|your article|your talk|your presentation|your interview)\b',
        r'\b(your linkedin|your twitter|your blog|your podcast)\b',
        r'\b(congratulations on|loved your|impressed by your)\b',
        r'\b(your company\'s|your team\'s|your product)\b'
    ]
    for pattern in specific_patterns:
        if re.search(pattern, content_lower):
            details['has_specific_reference'] = True
            details['indicators_found'].append('Specific research reference')
            score += 2
            break
    
    # 5. Custom opening (not generic) - 1 point
    generic_openings = [
        r'^(hi there|hello there|dear sir|dear madam|to whom|greetings)',
        r'^(hi,\s*$|hello,\s*$|hey,\s*$)'  # Just "Hi," with nothing after
    ]
    first_line = email_content.strip().split('\n')[0].lower().strip()
    is_generic = any(re.search(p, first_line) for p in generic_openings)
    
    # Check for personalized opening
    personalized_openings = [
        r'^(hi|hello|hey)\s+\{',  # Hi {Name}
        r'^(hi|hello|hey)\s+[a-z]+',  # Hi John (actual name)
    ]
    has_personal_greeting = any(re.search(p, first_line) for p in personalized_openings)
    
    if has_personal_greeting and not is_generic:
        details['has_custom_opening'] = True
        details['indicators_found'].append('Personalized greeting')
        score += 1
    
    # 6. Mutual connection reference - 1 point
    mutual_patterns = [
        r'\b(mutual connection|referred by|introduced by|mentioned you)\b',
        r'\b(we both know|we met at|spoke at|connected on)\b',
        r'\b(your colleague|your friend|recommended you)\b'
    ]
    for pattern in mutual_patterns:
        if re.search(pattern, content_lower):
            details['has_mutual_connection'] = True
            details['indicators_found'].append('Mutual connection')
            score += 1
            break
    
    # 7. Recent event/trigger (timeliness) - 1 point
    trigger_patterns = [
        r'\b(just (saw|read|heard|noticed)|recently|this week|today)\b',
        r'\b(your announcement|new funding|new role|promotion)\b',
        r'\b(congrats on|congratulations on the)\b'
    ]
    for pattern in trigger_patterns:
        if re.search(pattern, content_lower):
            details['has_recent_trigger'] = True
            details['indicators_found'].append('Timely trigger event')
            score += 1
            break
    
    # Cap score at 10
    score = min(score, 10)
    
    # Legacy compatibility
    details['has_name'] = details['has_name_placeholder']
    details['has_company'] = details['has_company_placeholder']
    
    return score, details

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

    # 2. Personalization Checker (Advanced Rule-Based + AI Enhancement)
    personalization_score, personalization_details = rule_based_personalization(email_content)
    
    # AI enhancement for context-aware personalization detection
    ai_personalization_boost = 0
    ai_feedback = None
    if current_user.can_analyze() and personalization_score < 7:
        # Only call AI if rule-based score is not already high
        prompt = (
            "Rate this email's personalization from 1-10. Consider:\n"
            "- Does it reference specific details about the recipient?\n"
            "- Does it feel templated or genuinely customized?\n"
            "- Is there evidence of research about the recipient?\n\n"
            "Reply with ONLY a number 1-10.\n\n"
            f"Email: {email_content[:800]}"
        )
        gpt_response = call_openai(prompt)
        if gpt_response:
            try:
                # Extract number from response
                ai_score = int(re.search(r'\d+', gpt_response).group())
                ai_score = min(10, max(1, ai_score))
                # Blend AI score with rule-based (AI can boost by up to 3 points)
                if ai_score > personalization_score:
                    ai_personalization_boost = min(3, ai_score - personalization_score)
                    personalization_details['ai_detected'] = True
                    personalization_details['indicators_found'].append('AI detected personalized tone')
            except:
                pass
    
    # Final personalization score (rule-based + AI boost)
    final_personalization_score = min(10, personalization_score + ai_personalization_boost)
    personalization_details['score'] = final_personalization_score
    personalization_details['rule_score'] = personalization_score
    personalization_details['ai_boost'] = ai_personalization_boost
    
    # Determine status label
    if final_personalization_score >= 7:
        personalization_status = 'EXCELLENT'
    elif final_personalization_score >= 5:
        personalization_status = 'GOOD'
    elif final_personalization_score >= 3:
        personalization_status = 'NEEDS WORK'
    else:
        personalization_status = 'POOR'

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
    merged_structure = structure_suggestion or (
        "Add more personalization elements like recipient name, company, or specific references." 
        if final_personalization_score < 5 else "Looks clear!"
    )
    
    # Compose overall score (Spam + Personalization + Subject)
    # Higher score = better, lower = worse
    # We'll use a 10-point scale, where 10 is best, 1 is worst
    # Start from 10, subtract for each issue
    # Note: spam_score internally is 1 (best) to 10 (worst)
    score = 10
    score -= (spam_score - 1)  # spam_score: 1 (best) to 10 (worst), so subtract (spam_score-1)
    
    # Personalization impact on overall score (weighted by new scoring)
    if final_personalization_score < 3:
        score -= 3  # Poor personalization = -3
    elif final_personalization_score < 5:
        score -= 2  # Needs work = -2
    elif final_personalization_score < 7:
        score -= 1  # Good but not excellent = -1
    # Excellent (7+) = no penalty
    
    if subject_grade not in ['A','B']:
        score -= 1
    overall_score = max(1, min(10, score))

    return {
        'spam_words_found': spam_words_found,
        'spam_score': 11 - spam_score,  # Convert to user-friendly: 1 (bad) -> 10 (good)
        'exclamations': exclamations,
        'all_caps': all_caps,
        'personalization': personalization_status,
        'personalization_score': final_personalization_score,
        'personalization_details': personalization_details,
        'has_name': personalization_details['has_name'],
        'has_company': personalization_details['has_company'],
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
                
                flash('Account created successfully! Please check your email to verify your account. You have 6 free ColdMail analyses.')
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
                
                flash(f'Welcome back! You have {user.get_remaining_analyses()} ColdMail analyses remaining.')
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
                        flash(f'Welcome back! You have {user.get_remaining_analyses()} ColdMail analyses remaining.')
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
    return render_template('upgrade.html', paypal_client_id=PAYPAL_CLIENT_ID)

@app.route('/paypal-checkout')
@login_required
def paypal_checkout():
    """Direct PayPal checkout page"""
    return render_template('upgrade.html', paypal_client_id=PAYPAL_CLIENT_ID)

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

@app.route('/create-payment', methods=['POST'])
@login_required
def create_payment():
    """Create a PayPal payment using the REST API"""
    try:
        # Create PayPal payment
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "transactions": [{
                "amount": {
                    "total": "20.00",
                    "currency": "USD"
                },
                "description": "ColdMail Unlimited Analyses Upgrade",
                "item_list": {
                    "items": [{
                        "name": "ColdMail Unlimited Analyses",
                        "sku": "unlimited_analyses",
                        "price": "20.00",
                        "currency": "USD",
                        "quantity": 1
                    }]
                }
            }],
            "redirect_urls": {
                "return_url": url_for('execute_payment', _external=True),
                "cancel_url": url_for('upgrade', _external=True)
            }
        })
        
        if payment.create():
            # Find the approval URL
            for link in payment.links:
                if link.rel == "approval_url":
                    return jsonify({
                        "id": payment.id,
                        "status": payment.state,
                        "approval_url": link.href
                    })
            
            return jsonify({
                "error": "Payment created but approval URL not found"
            }), 500
        else:
            error_message = payment.error.get('message', 'Unknown error')
            return jsonify({
                "error": error_message,
                "details": payment.error
            }), 400
            
    except Exception as e:
        print(f"Error creating PayPal payment: {e}")
        return jsonify({
            "error": "Internal server error"
        }), 500

@app.route('/execute-payment/<payment_id>')
@login_required
def execute_payment(payment_id):
    """Execute a PayPal payment after approval"""
    try:
        payer_id = request.args.get('PayerID')
        if not payer_id:
            flash('Payment approval failed - missing Payer ID')
            return redirect(url_for('upgrade'))
        
        # Find the payment
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if not payment:
            flash('Payment not found')
            return redirect(url_for('upgrade'))
        
        # Execute the payment
        if payment.execute({"payer_id": payer_id}):
            # Check if payment was successful
            if payment.state == "approved":
                # Mark user as paid
                current_user.mark_paid()
                db.session.commit()
                
                # Send confirmation email
                send_payment_confirmation(current_user.email)
                
                flash('Payment successful! You now have unlimited analyses.')
                return redirect(url_for('home'))
            else:
                flash(f'Payment not approved. Status: {payment.state}')
                return redirect(url_for('upgrade'))
        else:
            error_message = payment.error.get('message', 'Unknown error')
            flash(f'Payment execution failed: {error_message}')
            return redirect(url_for('upgrade'))
            
    except Exception as e:
        print(f"Error executing PayPal payment: {e}")
        flash('Payment execution failed. Please try again.')
        return redirect(url_for('upgrade'))

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
    # Check for payment success parameter
    payment_success = request.args.get('payment') == 'success'
    
    if current_user.is_authenticated:
        remaining = current_user.get_remaining_analyses()
        print(f"User {current_user.email} is authenticated, remaining analyses: {remaining}")
        
        if payment_success:
            flash('🎉 Payment successful! You now have unlimited analyses.')
            
        return render_template('index.html', remaining=remaining, paid=current_user.is_paid)
    else:
        print("No user is currently authenticated")
    return render_template('index.html', remaining="3", paid=False)

@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    if not current_user.can_analyze():
        if current_user.is_paid:
            flash('Monthly fair use limit reached (200/month). Your limit resets at the start of next month.')
            return redirect(url_for('home'))
        else:
            flash('Free tier limit reached. Please upgrade for 200 analyses per month!')
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

# --- Prompt Improver Feature ---
def improve_prompt_with_ai(original_prompt):
    """Use AI to analyze and improve a prompt for AI app builders"""
    if not OPENAI_API_KEY:
        return None, None
    
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    # First, get analysis of the prompt
    analysis_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are an expert at analyzing prompts for AI app builders (like Cursor, v0, Bolt, Lovable, Replit Agent). Analyze the given prompt and provide a brief analysis covering: 1) Clarity (is it clear what app/feature is being requested?), 2) Technical Specificity (does it specify tech stack, frameworks, or styling preferences?), 3) Feature Details (are the features and functionality clearly described?), 4) UI/UX Requirements (does it describe the look, feel, or user flow?). Keep your analysis concise - 2-3 sentences per point."},
            {"role": "user", "content": f"Analyze this AI app builder prompt:\n\n{original_prompt[:1500]}"}
        ],
        "max_tokens": 400,
        "temperature": 0.3
    }
    
    # Then, get the improved version
    improvement_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are an expert at writing prompts for AI app builders (Cursor, v0, Bolt, Lovable, Replit Agent). Your job is to take a developer's vague or basic prompt and transform it into a detailed, specific prompt that will generate better code and features. Include: specific tech stack preferences if apparent, detailed feature descriptions, UI/UX requirements, component structure, styling preferences, and any edge cases. Make the prompt comprehensive but organized. Output ONLY the improved prompt, nothing else."},
            {"role": "user", "content": f"Improve this AI app builder prompt:\n\n{original_prompt[:1500]}"}
        ],
        "max_tokens": 800,
        "temperature": 0.4
    }
    
    analysis = None
    improved = None
    
    try:
        # Get analysis
        response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=analysis_data, timeout=15)
        response.raise_for_status()
        analysis = response.json()['choices'][0]['message']['content'].strip()
        
        # Get improved prompt
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
    
    # Check for tech stack/framework mentions
    tech_patterns = [
        r'(react|vue|angular|svelte|next\.?js|nuxt|remix)',
        r'(tailwind|bootstrap|css|styled-components|chakra|material)',
        r'(node|express|flask|django|fastapi|rails)',
        r'(typescript|javascript|python|rust|go)',
        r'(postgres|mongodb|mysql|sqlite|supabase|firebase)',
        r'(api|rest|graphql|websocket)'
    ]
    for pattern in tech_patterns:
        if re.search(pattern, prompt_lower):
            analysis['has_tech_stack'] = True
            analysis['strengths'].append('Specifies tech stack or framework')
            break
    
    if not analysis['has_tech_stack']:
        analysis['issues'].append('No tech stack specified - consider adding preferred frameworks (React, Tailwind, etc.)')
    
    # Check for feature/component descriptions
    feature_patterns = [
        r'(button|form|modal|navbar|sidebar|card|table|list|grid)',
        r'(login|signup|auth|dashboard|profile|settings|admin)',
        r'(search|filter|sort|pagination|infinite scroll)',
        r'(upload|download|export|import|share)',
        r'(notification|alert|toast|message)',
        r'(chart|graph|analytics|metrics|stats)'
    ]
    for pattern in feature_patterns:
        if re.search(pattern, prompt_lower):
            analysis['has_feature_description'] = True
            analysis['strengths'].append('Describes specific features or components')
            break
    
    if not analysis['has_feature_description']:
        analysis['issues'].append('Missing feature details - describe specific components and features you want')
    
    # Check for UI/UX requirements
    ui_patterns = [
        r'(responsive|mobile|desktop|tablet)',
        r'(dark mode|light mode|theme)',
        r'(layout|grid|flex|centered|sidebar)',
        r'(animation|transition|hover|smooth)',
        r'(modern|clean|minimal|professional|sleek)',
        r'(user-friendly|intuitive|accessible)'
    ]
    for pattern in ui_patterns:
        if re.search(pattern, prompt_lower):
            analysis['has_ui_requirements'] = True
            analysis['strengths'].append('Includes UI/UX requirements')
            break
    
    if not analysis['has_ui_requirements']:
        analysis['issues'].append('No UI preferences - describe the look and feel you want (modern, minimal, responsive, etc.)')
    
    # Check for functionality descriptions
    functionality_patterns = [
        r'(crud|create|read|update|delete)',
        r'(fetch|load|save|store|display)',
        r'(validate|check|verify|confirm)',
        r'(when|if|after|before|on click|on submit)',
        r'(user can|should be able to|allow|enable)'
    ]
    for pattern in functionality_patterns:
        if re.search(pattern, prompt_lower):
            analysis['has_functionality'] = True
            analysis['strengths'].append('Describes functionality and user actions')
            break
    
    if not analysis['has_functionality']:
        analysis['issues'].append('Missing functionality details - explain what users should be able to do')
    
    # Check for styling preferences
    styling_patterns = [
        r'(color|colours?|blue|green|red|purple|gradient)',
        r'(font|typography|text|heading)',
        r'(spacing|padding|margin|gap)',
        r'(border|rounded|shadow|blur)',
        r'(icon|image|logo|avatar)'
    ]
    for pattern in styling_patterns:
        if re.search(pattern, prompt_lower):
            analysis['has_styling'] = True
            analysis['strengths'].append('Includes styling preferences')
            break
    
    if not analysis['has_styling']:
        analysis['issues'].append('No styling details - consider specifying colors, fonts, or visual style')
    
    # Calculate score
    score = 2  # Base score
    if analysis['has_tech_stack']: score += 2
    if analysis['has_feature_description']: score += 2
    if analysis['has_ui_requirements']: score += 2
    if analysis['has_functionality']: score += 1
    if analysis['has_styling']: score += 1
    
    # Length considerations
    if analysis['word_count'] < 10:
        score -= 1
        analysis['issues'].append('Prompt is too short - AI builders work better with detailed prompts')
    elif analysis['word_count'] > 500:
        analysis['strengths'].append('Detailed prompt - good for complex apps')
    
    analysis['score'] = min(10, max(1, score))
    
    return analysis

@app.route('/improve-prompt', methods=['POST'])
@login_required
def improve_prompt():
    if not current_user.can_analyze():
        if current_user.is_paid:
            flash('Monthly fair use limit reached (200/month). Your limit resets at the start of next month.')
            return redirect(url_for('home'))
        else:
            flash('Free tier limit reached. Please upgrade for 200 analyses per month!')
            return redirect(url_for('upgrade'))
    
    prompt_content = request.form.get('prompt_content', '')
    if not prompt_content.strip():
        flash('Please enter a prompt to improve.')
        return redirect(url_for('home'))
    
    # Analyze the prompt
    rule_analysis = rule_based_prompt_analysis(prompt_content)
    ai_analysis, improved_prompt = improve_prompt_with_ai(prompt_content)
    
    # Store results in session
    session['prompt_result'] = {
        'original_prompt': prompt_content,
        'improved_prompt': improved_prompt or '(Could not generate improved prompt. Please try again.)',
        'ai_analysis': ai_analysis,
        'rule_analysis': rule_analysis
    }
    
    # Increment analysis count
    current_user.increment_analysis()
    
    return redirect(url_for('prompt_result'))

@app.route('/prompt-result')
@login_required
def prompt_result():
    prompt_data = session.get('prompt_result', {})
    
    if not prompt_data:
        return redirect(url_for('home'))
    
    return render_template('prompt_result.html', 
                         prompt_data=prompt_data,
                         paid=current_user.is_paid)

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