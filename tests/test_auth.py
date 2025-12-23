import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base_class import Base
from app.db.session import get_db
from app.core.deps import get_supabase_client
from app.models import User


@pytest.fixture(scope="session")
def _engine():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(_engine):
    connection = _engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()

    # Nested transaction so app code can call commit() freely.
    nested = connection.begin_nested()

    from sqlalchemy import event
    from sqlalchemy.orm import Session

    @event.listens_for(Session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        nonlocal nested
        if trans.nested and not trans._parent.nested:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def _supabase_auth_response(
    *,
    user_id: str | None,
    access_token: str | None = None,
    refresh_token: str = "refresh",
    expires_in: int = 3600,
):
    user = None if user_id is None else SimpleNamespace(id=user_id)
    session = None
    if access_token is not None:
        session = SimpleNamespace(access_token=access_token, refresh_token=refresh_token, expires_in=expires_in)
    return SimpleNamespace(user=user, session=session)


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def test_signup_success_creates_profile_and_returns_token(client, db_session, monkeypatch):
    user_id = str(uuid.uuid4())
    access_token = "access-token-123"

    supabase = SimpleNamespace(
        auth=SimpleNamespace(
            sign_up=lambda payload: _supabase_auth_response(user_id=user_id, access_token=access_token)
        )
    )
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    payload = {"email": "user@example.com", "password": "SecurePassword123!", "username": "newuser"}
    resp = client.post("/api/v1/auth/signup", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"] == access_token
    assert body["token_type"] == "bearer"

    created = db_session.query(User).filter(User.username == "newuser").first()
    assert created is not None
    assert str(created.id) == user_id


def test_signup_username_taken_returns_400(client, db_session):
    existing = User(id=uuid.uuid4(), username="taken")
    db_session.add(existing)
    db_session.commit()

    supabase = SimpleNamespace(auth=SimpleNamespace(sign_up=lambda payload: pytest.fail("should not call supabase")))
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    payload = {"email": "user@example.com", "password": "SecurePassword123!", "username": "taken"}
    resp = client.post("/api/v1/auth/signup", json=payload)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Username already taken"


def test_signup_supabase_returns_no_user_returns_400(client):
    supabase = SimpleNamespace(
        auth=SimpleNamespace(
            sign_up=lambda payload: _supabase_auth_response(user_id=None, access_token="x")
        )
    )
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    payload = {"email": "user@example.com", "password": "SecurePassword123!", "username": "nouser"}
    resp = client.post("/api/v1/auth/signup", json=payload)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Failed to create user account"


def test_signup_missing_access_token_returns_500(client):
    user_id = str(uuid.uuid4())
    supabase = SimpleNamespace(
        auth=SimpleNamespace(
            sign_up=lambda payload: _supabase_auth_response(user_id=user_id, access_token=None)
        )
    )
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    payload = {"email": "user@example.com", "password": "SecurePassword123!", "username": "notoken"}
    resp = client.post("/api/v1/auth/signup", json=payload)
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Failed to generate access token"


def test_signup_malicious_username_rejected_before_supabase(client):
    calls = {}

    def _should_not_call(_payload):
        calls["called"] = True

    supabase = SimpleNamespace(auth=SimpleNamespace(sign_up=_should_not_call))
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    payload = {"email": "evil@example.com", "password": "SecurePassword123!", "username": "<script></script>\x00"}
    resp = client.post("/api/v1/auth/signup", json=payload)

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid username"
    assert "called" not in calls


def test_login_success_returns_token(client):
    access_token = "access-token-abc"
    supabase = SimpleNamespace(
        auth=SimpleNamespace(
            sign_in_with_password=lambda payload: _supabase_auth_response(
                user_id=str(uuid.uuid4()),
                access_token=access_token,
            )
        )
    )
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    payload = {"email": "user@example.com", "password": "SecurePassword123!"}
    resp = client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] == access_token
    assert body["token_type"] == "bearer"


def test_login_invalid_credentials_returns_401(client):
    supabase = SimpleNamespace(
        auth=SimpleNamespace(
            sign_in_with_password=lambda payload: _supabase_auth_response(user_id=str(uuid.uuid4()), access_token=None)
        )
    )
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    payload = {"email": "user@example.com", "password": "wrong"}
    resp = client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


def test_password_reset_request_always_returns_success_even_on_error(client):
    def _raise(_email):
        raise RuntimeError("email service down")

    supabase = SimpleNamespace(auth=SimpleNamespace(reset_password_email=_raise))
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    resp = client.post("/api/v1/auth/password-reset/request", json={"email": "user@example.com"})
    assert resp.status_code == 200
    assert "reset link" in resp.json()["message"]


def test_password_reset_confirm_success(client):
    user_id = str(uuid.uuid4())
    access_token = "access-token-reset"
    refresh_token = "refresh-token-reset"

    auth = SimpleNamespace(
        verify_otp=lambda payload: _supabase_auth_response(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
        ),
        set_session=lambda access_token, refresh_token: None,
        update_user=lambda payload: SimpleNamespace(user=SimpleNamespace(id=user_id)),
    )
    supabase = SimpleNamespace(auth=auth)
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    resp = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "tokenhash", "password": "NewSecurePassword123!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "Password has been reset successfully"
    assert body["access_token"] == access_token
    assert body["token_type"] == "bearer"


def test_password_reset_confirm_invalid_token_returns_400(client):
    auth = SimpleNamespace(
        verify_otp=lambda payload: _supabase_auth_response(user_id=None, access_token="x"),
        set_session=lambda access_token, refresh_token: None,
        update_user=lambda payload: SimpleNamespace(user=SimpleNamespace(id=str(uuid.uuid4()))),
    )
    supabase = SimpleNamespace(auth=auth)
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    resp = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "badtoken", "password": "NewSecurePassword123!"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid or expired reset token"


def test_password_reset_confirm_update_fails_returns_400(client):
    user_id = str(uuid.uuid4())
    auth = SimpleNamespace(
        verify_otp=lambda payload: _supabase_auth_response(user_id=user_id, access_token="at", refresh_token="rt"),
        set_session=lambda access_token, refresh_token: None,
        update_user=lambda payload: SimpleNamespace(user=None),
    )
    supabase = SimpleNamespace(auth=auth)
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    resp = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "tokenhash", "password": "NewSecurePassword123!"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Failed to update password"


def test_refresh_token_success_returns_new_tokens(client):
    access_token = "new-access-token"
    refresh_token = "new-refresh-token"

    supabase = SimpleNamespace(
        auth=SimpleNamespace(
            refresh_session=lambda refresh: _supabase_auth_response(
                user_id=str(uuid.uuid4()),
                access_token=access_token,
                refresh_token=refresh_token,
            )
        )
    )
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "old-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] == access_token
    assert body["refresh_token"] == refresh_token
    assert body["token_type"] == "bearer"


def test_refresh_token_invalid_returns_401(client):
    supabase = SimpleNamespace(
        auth=SimpleNamespace(
            refresh_session=lambda refresh: _supabase_auth_response(
                user_id=None,
                access_token=None,
            )
        )
    )
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "bad-token"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid or expired refresh token"


def test_logout_revokes_session(client):
    calls = {}

    def _get_user(token):
        calls["token"] = token
        return SimpleNamespace(user=SimpleNamespace(id=str(uuid.uuid4())))

    def _sign_out(payload):
        calls["scope"] = payload.get("scope") if isinstance(payload, dict) else None

    supabase = SimpleNamespace(auth=SimpleNamespace(get_user=_get_user, sign_out=_sign_out))
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    resp = client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer logout-token"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Successfully logged out"
    assert calls["token"] == "logout-token"
    assert calls["scope"] == "global"


def test_logout_invalid_token_returns_401(client):
    supabase = SimpleNamespace(
        auth=SimpleNamespace(
            get_user=lambda token: SimpleNamespace(user=None),
            sign_out=lambda payload: None,
        )
    )
    app.dependency_overrides[get_supabase_client] = lambda: supabase

    resp = client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer bad-token"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid token"


def test_logout_missing_authorization_header_returns_403(client):
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Not authenticated"
