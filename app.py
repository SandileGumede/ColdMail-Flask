from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User
import re
import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import paypalrestsdk

load_dotenv()
import os
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
print('OPENAI_API_KEY loaded:', OPENAI_API_KEY)

PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET')

paypalrestsdk.configure({
    "mode": "live",  # Change to "live" for production
    "client_id": PAYPAL_CLIENT_ID or "AbQ4QCanvZ1VWcuAhwWPrNHiU3dZvbjGQu2SbiyatTjoQuuxQnIiIqo5I4E74XBlodmsOZGb3sTvQL99",
    "client_secret": PAYPAL_CLIENT_SECRET or "EJXtIcTxaWLa-uVMIyYZpXC89qSQF-ElyFFQLVbMs_wbsV_EbEHyPj0Q0MTXAaPnpxE-JVfTb7ytHdvO"
})

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
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

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
setattr(login_manager, 'login_view', 'login')
login_manager.login_message = 'Please log in to access this feature.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.')
            return redirect(url_for('login'))
        
        user = User()  # Fixed: Don't pass email to constructor
        user.email = email  # Set email attribute directly
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user, remember=True)
        flash('Account created successfully! You have 3 free ColdMail analyses.')
        return redirect(url_for('home'))
    
    return render_template('auth/signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # Fix: Ensure remember is a boolean
        remember = request.form.get('remember') == 'on'
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome back! You have {user.get_remaining_analyses()} ColdMail analyses remaining.')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out of ColdMail.')
    return redirect(url_for('home'))

@app.route('/upgrade')
@login_required
def upgrade():
    return render_template('upgrade.html')

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
        return render_template('index.html', remaining=remaining, paid=current_user.is_paid)
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
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})

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
            db.engine.execute('SELECT 1')
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
        
        # Try alternative approach
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