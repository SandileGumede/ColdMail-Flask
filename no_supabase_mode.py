"""
Fallback mode when Supabase is not available or has issues
This allows the app to run with local authentication only
"""

from models import User, db
from flask_login import login_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class NoSupabaseService:
    """Fallback service that provides local authentication only"""
    
    def __init__(self):
        self.is_available = False  # Always False for this fallback service
        print("ℹ️  Running in local authentication mode (no Supabase)")
    
    def sign_up(self, email: str, password: str):
        """Sign up a new user with local authentication only"""
        try:
            # Create user in local database only
            user = User()
            user.email = email
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            return {
                "success": True,
                "user": user,
                "supabase_user": None
            }
                
        except Exception as e:
            logger.error(f"Local sign up error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def sign_in(self, email: str, password: str):
        """Sign in user with local authentication only"""
        try:
            # Find user in local database
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                return {
                    "success": True,
                    "user": user,
                    "supabase_user": None
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid credentials"
                }
                
        except Exception as e:
            logger.error(f"Local sign in error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def sign_out(self):
        """Sign out user (local only)"""
        return {"success": True}
    
    def get_user(self, user_id: str):
        """Get user from local database"""
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return None
    
    def update_user_profile(self, user_id: str, updates: dict):
        """Update user profile in local database"""
        try:
            user = User.query.get(int(user_id))
            if user:
                for key, value in updates.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                db.session.commit()
                return user
            return None
        except Exception as e:
            logger.error(f"Update user error: {e}")
            return None
    
    def reset_password(self, email: str):
        """Password reset not available in local mode"""
        return {
            "success": False, 
            "error": "Password reset not available in local authentication mode"
        }
    
    def verify_email(self, token: str, type: str):
        """Email verification not available in local mode"""
        return None













