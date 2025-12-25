import sys
from pathlib import Path
import os
import uuid
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
# Allow models that use PostgreSQL UUID columns to be created under SQLite.
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import BigInteger

# Ensure the application package is importable when running tests without installation
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Provide required defaults for settings instantiation during module import
os.environ.setdefault("SECRET_KEY", "test-secret-key")


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(_type, _compiler, **_kw):
    return "CHAR(36)"


@compiles(BigInteger, "sqlite")
def _compile_biginteger_sqlite(_type, _compiler, **_kw):
    """Render BigInteger as INTEGER in SQLite with autoincrement support."""
    return "INTEGER"


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    from app.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    """Ensure test dependency overrides don't leak across tests."""
    from app.main import app
    yield
    app.dependency_overrides.clear()


def cleanup_supabase_user(user_id: str):
    """
    Helper function to cleanup Supabase user after test.
    
    This function should be called in test cleanup to delete users created
    during signup tests. It requires Supabase service role key for admin operations.
    
    Args:
        user_id: The UUID of the user to delete
        
    Note: This requires SUPABASE_SERVICE_ROLE_KEY to be set in environment.
    For unit tests with mocks, this is not needed.
    """
    try:
        from app.core.config import settings
        from app.db.session import SessionLocal
        from app.models import User
        
        # Delete from database first
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                db.delete(user)
                db.commit()
        finally:
            db.close()
        
        # For actual Supabase cleanup, you would need service role key
        # This is typically only done in integration tests, not unit tests
        if settings.SUPABASE_SERVICE_ROLE_KEY:
            from supabase import create_client
            admin_client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
            # Delete from Supabase Auth (requires admin privileges)
            admin_client.auth.admin.delete_user(user_id)
            print(f"Note: User {user_id} deleted from database. Manual Supabase Auth cleanup may be needed.")
        else:
            print(f"Note: User {user_id} deleted from database only. Set SUPABASE_SERVICE_ROLE_KEY for full cleanup.")
            
    except Exception as e:
        print(f"Warning: Failed to cleanup user {user_id}: {e}")


def generate_unique_email():
    """Generate a unique email for testing"""
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


def generate_unique_username():
    """Generate a unique username for testing"""
    return f"testuser_{uuid.uuid4().hex[:8]}"

