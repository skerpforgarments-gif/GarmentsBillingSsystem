import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# =========================================================
# LOAD FROM ENV (PRODUCTION SAFE)
# =========================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Supabase credentials not set in environment variables")

# =========================================================
# CREATE CLIENT (SINGLETON)
# =========================================================
# We use a standard initialization. If the 'refresh_token_timer' error 
# occurs on exit, it's a known Supabase library bug that doesn't 
# affect functionality during app runtime.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================================================
# OPTIONAL: AUTH HELPERS
# =========================================================
class SupabaseAuth:
    @staticmethod
    def sign_up(email: str, password: str):
        return supabase.auth.sign_up({
            "email": email,
            "password": password
        })

    @staticmethod
    def sign_in(email: str, password: str):
        return supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

    @staticmethod
    def sign_out():
        return supabase.auth.sign_out()

    @staticmethod
    def get_user():
        return supabase.auth.get_user()
