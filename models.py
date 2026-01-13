from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

db = SQLAlchemy()

# Fair use limit for paid users (per month)
MONTHLY_ANALYSIS_LIMIT = 200

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    user_name = db.Column(db.String(12), unique=True, nullable=True)  # Username max 12 characters
    password_hash = db.Column(db.String(255), nullable=True)  # Made nullable for Supabase users
    supabase_id = db.Column(db.String(255), unique=True, nullable=True)  # Supabase user ID
    analysis_count = db.Column(db.Integer, default=0)  # Total lifetime analyses (free tier tracking)
    is_paid = db.Column(db.Boolean, default=False)
    payment_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    email_verified = db.Column(db.Boolean, default=False)
    
    # Monthly usage tracking for fair use policy
    monthly_analysis_count = db.Column(db.Integer, default=0)
    monthly_reset_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        # For Supabase users, password verification is handled by Supabase
        if self.supabase_id:
            return True  # Password verification handled by Supabase
        return check_password_hash(self.password_hash, password)
    
    def _check_monthly_reset(self):
        """Reset monthly count if we're in a new month"""
        now = datetime.utcnow()
        if self.monthly_reset_date is None:
            self.monthly_reset_date = now
            self.monthly_analysis_count = 0
            return
        
        # Check if we're in a new month
        if (now.year > self.monthly_reset_date.year or 
            (now.year == self.monthly_reset_date.year and now.month > self.monthly_reset_date.month)):
            self.monthly_analysis_count = 0
            self.monthly_reset_date = now
            db.session.commit()
    
    def can_analyze(self):
        """Check if user can perform analysis (free tier or paid with fair use limit)"""
        if self.is_paid:
            self._check_monthly_reset()
            return self.monthly_analysis_count < MONTHLY_ANALYSIS_LIMIT
        return self.analysis_count < 3
    
    def increment_analysis(self):
        """Increment analysis count"""
        if self.is_paid:
            self._check_monthly_reset()
            self.monthly_analysis_count += 1
        else:
            self.analysis_count += 1
        db.session.commit()
    
    def mark_paid(self):
        """Mark user as paid"""
        self.is_paid = True
        self.payment_date = datetime.utcnow()
        # Reset monthly count when user upgrades
        self.monthly_analysis_count = 0
        self.monthly_reset_date = datetime.utcnow()
        db.session.commit()
    
    def get_remaining_analyses(self):
        """Get remaining analyses for the current period"""
        if self.is_paid:
            self._check_monthly_reset()
            remaining = MONTHLY_ANALYSIS_LIMIT - self.monthly_analysis_count
            return f"{remaining}/month"
        return max(0, 3 - self.analysis_count)
    
    def get_monthly_usage(self):
        """Get current monthly usage stats for paid users"""
        if self.is_paid:
            self._check_monthly_reset()
            return {
                'used': self.monthly_analysis_count,
                'limit': MONTHLY_ANALYSIS_LIMIT,
                'remaining': MONTHLY_ANALYSIS_LIMIT - self.monthly_analysis_count
            }
        return None 