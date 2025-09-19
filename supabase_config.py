import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseConfig:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_ANON_KEY")
        self.service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.url or not self.key:
            print("⚠️  WARNING: SUPABASE_URL and SUPABASE_ANON_KEY not set!")
            print("   Supabase features will be disabled.")
            print("   Please set these environment variables in your Render dashboard.")
            self.client = None
            return
        
        try:
            # Create client with positional arguments (compatible with 2.3.4)
            self.client: Client = create_client(self.url, self.key)
            print("✅ Supabase client initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Supabase client: {e}")
            print(f"   Error type: {type(e).__name__}")
            print("   This might be a version compatibility issue.")
            self.client = None
        
    def get_client(self) -> Client:
        """Get the Supabase client instance"""
        return self.client
    
    def get_service_client(self) -> Client:
        """Get Supabase client with service key for admin operations"""
        if not self.service_key:
            raise ValueError("SUPABASE_SERVICE_KEY must be set for admin operations")
        return create_client(self.url, self.service_key)

# Global instance
supabase_config = SupabaseConfig()
