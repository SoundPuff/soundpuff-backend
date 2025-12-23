from functools import lru_cache
from typing import Optional

from supabase import Client, create_client

from app.core.config import settings


def _validate_basic_config(url: Optional[str], key: Optional[str], key_name: str) -> None:
    if not url or not key:
        raise ValueError(
            f"Supabase configuration is missing. Please set SUPABASE_URL and {key_name} in .env"
        )


@lru_cache(maxsize=1)
def _anon_client(url: str, key: str) -> Client:
    return create_client(url, key)


@lru_cache(maxsize=1)
def _admin_client(url: str, key: str) -> Client:
    return create_client(url, key)


def get_supabase_client() -> Client:
    """Get (and cache) Supabase client instance."""
    _validate_basic_config(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY, "SUPABASE_ANON_KEY")
    return _anon_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


def get_supabase_admin_client() -> Client:
    """Get (and cache) Supabase admin client with service role key (for admin operations)."""
    _validate_basic_config(
        settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY, "SUPABASE_SERVICE_ROLE_KEY"
    )
    return _admin_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
