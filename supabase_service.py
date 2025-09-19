from supabase_config import supabase_config
from models import User, db
from flask_login import login_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SupabaseService:
    def __init__(self):
        self.client = supabase_config.get_client()
        self.service_client = supabase_config.get_service_client() if supabase_config.service_key else None
        self.is_available = self.client is not None
    
    def sign_up(self, email: str, password: str):
        """Sign up a new user with Supabase Auth"""
        if not self.is_available:
            return {
                "success": False,
                "error": "Supabase not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables."
            }
        
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user:
                # Create user in our local database
                user = User()
                user.email = email
                user.supabase_id = response.user.id
                user.set_password(password)  # Keep local password for compatibility
                
                db.session.add(user)
                db.session.commit()
                
                return {
                    "success": True,
                    "user": user,
                    "supabase_user": response.user
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create user"
                }
                
        except Exception as e:
            logger.error(f"Sign up error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def sign_in(self, email: str, password: str):
        """Sign in user with Supabase Auth"""
        if not self.is_available:
            return {
                "success": False,
                "error": "Supabase not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables."
            }
        
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                # Find user in our local database
                user = User.query.filter_by(supabase_id=response.user.id).first()
                if not user:
                    # Fallback to email lookup for existing users
                    user = User.query.filter_by(email=email).first()
                    if user:
                        user.supabase_id = response.user.id
                        db.session.commit()
                
                if user:
                    return {
                        "success": True,
                        "user": user,
                        "supabase_user": response.user
                    }
                else:
                    return {
                        "success": False,
                        "error": "User not found in local database"
                    }
            else:
                return {
                    "success": False,
                    "error": "Invalid credentials"
                }
                
        except Exception as e:
            logger.error(f"Sign in error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def sign_out(self):
        """Sign out user from Supabase"""
        try:
            self.client.auth.sign_out()
            return {"success": True}
        except Exception as e:
            logger.error(f"Sign out error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_user(self, user_id: str):
        """Get user from Supabase by ID"""
        try:
            response = self.client.auth.get_user(user_id)
            return response.user if response.user else None
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return None
    
    def update_user_profile(self, user_id: str, updates: dict):
        """Update user profile in Supabase"""
        try:
            response = self.client.auth.update_user({
                "id": user_id,
                **updates
            })
            return response.user if response.user else None
        except Exception as e:
            logger.error(f"Update user error: {e}")
            return None
    
    def reset_password(self, email: str):
        """Send password reset email"""
        try:
            response = self.client.auth.reset_password_email(email)
            return {"success": True, "message": "Password reset email sent"}
        except Exception as e:
            logger.error(f"Password reset error: {e}")
            return {"success": False, "error": str(e)}
    
    def verify_email(self, token: str, type: str):
        """Verify email with token"""
        try:
            response = self.client.auth.verify_otp({
                "token": token,
                "type": type
            })
            return response.user if response.user else None
        except Exception as e:
            logger.error(f"Email verification error: {e}")
            return None
