from supabase import create_client, Client
from app.core.config import settings
from typing import Optional


def get_supabase_client() -> Client:
    """Get Supabase client instance"""
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise ValueError("Supabase configuration is missing. Please set SUPABASE_URL and SUPABASE_ANON_KEY in .env")

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


def get_supabase_admin_client() -> Client:
    """Get Supabase admin client with service role key (for admin operations)"""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Supabase admin configuration is missing. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
