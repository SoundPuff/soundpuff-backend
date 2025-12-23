from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache(maxsize=4)
def _cached_create_client(url: str, key: str) -> Client:
    return create_client(url, key)


def clear_supabase_client_cache() -> None:
    """Clear cached Supabase clients.

    Useful in tests where settings may be patched.
    """
    _cached_create_client.cache_clear()


def get_supabase_client() -> Client:
    """Get Supabase client instance"""
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise ValueError("Supabase configuration is missing. Please set SUPABASE_URL and SUPABASE_ANON_KEY in .env")

    return _cached_create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


def get_supabase_admin_client() -> Client:
    """Get Supabase admin client with service role key (for admin operations)"""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Supabase admin configuration is missing. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")

    return _cached_create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
