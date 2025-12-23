from typing import Optional

from supabase import Client, create_client

from app.core.config import settings

# Cache Supabase clients so we don't pay connection setup on every request
_anon_client: Optional[Client] = None
_admin_client: Optional[Client] = None


def _build_client(url: str, key: str) -> Client:
    return create_client(url, key)


def get_supabase_client() -> Client:
    """Get (and cache) Supabase client instance"""
    global _anon_client
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise ValueError(
            "Supabase configuration is missing. Please set SUPABASE_URL and SUPABASE_ANON_KEY in .env"
        )

    if _anon_client is None:
        _anon_client = _build_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _anon_client


def get_supabase_admin_client() -> Client:
    """Get (and cache) Supabase admin client with service role key (for admin operations)"""
    global _admin_client
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError(
            "Supabase admin configuration is missing. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env"
        )

    if _admin_client is None:
        _admin_client = _build_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _admin_client
