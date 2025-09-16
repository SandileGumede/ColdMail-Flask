from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Made nullable for Supabase users
    supabase_id = db.Column(db.String(255), unique=True, nullable=True)  # Supabase user ID
    analysis_count = db.Column(db.Integer, default=0)
    is_paid = db.Column(db.Boolean, default=False)
    payment_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    email_verified = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        # For Supabase users, password verification is handled by Supabase
        if self.supabase_id:
            return True  # Password verification handled by Supabase
        return check_password_hash(self.password_hash, password)
    
    def can_analyze(self):
        """Check if user can perform analysis (free tier or paid)"""
        return self.is_paid or self.analysis_count < 3
    
    def increment_analysis(self):
        """Increment analysis count for free tier users"""
        if not self.is_paid:
            self.analysis_count += 1
            db.session.commit()
    
    def mark_paid(self):
        """Mark user as paid"""
        self.is_paid = True
        self.payment_date = datetime.utcnow()
        db.session.commit()
    
    def get_remaining_analyses(self):
        """Get remaining free analyses"""
        if self.is_paid:
            return "Unlimited"
        return max(0, 3 - self.analysis_count) 