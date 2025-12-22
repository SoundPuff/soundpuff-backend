import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base_class import Base
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models import User, Follow, Like, Playlist


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


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


@pytest.fixture
def current_user(db_session):
    """Create a test user to represent the authenticated user."""
    user = User(id=uuid.uuid4(), username="currentuser", bio="Test bio")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_user(db_session):
    """Create another test user."""
    user = User(id=uuid.uuid4(), username="otheruser", bio="Other bio")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def third_user(db_session):
    """Create a third test user for follower/following tests."""
    user = User(id=uuid.uuid4(), username="thirduser", bio="Third bio")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ==================== GET /me tests ====================


def test_read_current_user_success(client, current_user):
    """Test retrieving the current authenticated user's profile."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "currentuser"
    assert body["bio"] == "Test bio"
    assert body["id"] == str(current_user.id)


def test_read_current_user_no_auth_returns_403(client):
    """Test that /me endpoint returns 403 without auth."""
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 403


# ==================== PUT /me tests ====================


def test_update_current_user_bio(client, current_user, db_session):
    """Test updating the current user's bio."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.put("/api/v1/users/me", json={"bio": "Updated bio"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["bio"] == "Updated bio"
    assert body["username"] == "currentuser"

    # Verify in DB
    refreshed = db_session.query(User).filter(User.id == current_user.id).first()
    assert refreshed.bio == "Updated bio"


def test_update_current_user_avatar_url(client, current_user, db_session):
    """Test updating the current user's avatar_url."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    new_avatar = "https://example.com/avatar.jpg"
    resp = client.put("/api/v1/users/me", json={"avatar_url": new_avatar})
    assert resp.status_code == 200
    body = resp.json()
    assert body["avatar_url"] == new_avatar

    # Verify in DB
    refreshed = db_session.query(User).filter(User.id == current_user.id).first()
    assert refreshed.avatar_url == new_avatar


def test_update_current_user_both_fields(client, current_user, db_session):
    """Test updating both bio and avatar_url at once."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.put(
        "/api/v1/users/me",
        json={"bio": "New bio", "avatar_url": "https://example.com/new.jpg"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["bio"] == "New bio"
    assert body["avatar_url"] == "https://example.com/new.jpg"


def test_update_current_user_partial_update(client, current_user):
    """Test that updating only one field doesn't affect the other."""
    app.dependency_overrides[get_current_user] = lambda: current_user
    original_avatar = current_user.avatar_url

    resp = client.put("/api/v1/users/me", json={"bio": "Only bio update"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["bio"] == "Only bio update"
    assert body["avatar_url"] == original_avatar


def test_update_current_user_no_auth_returns_403(client):
    """Test that PUT /me returns 403 without auth."""
    resp = client.put("/api/v1/users/me", json={"bio": "test"})
    assert resp.status_code == 403


# ==================== GET /{username} tests ====================


def test_read_user_by_username_success(client, other_user):
    """Test retrieving a user by username."""
    resp = client.get(f"/api/v1/users/{other_user.username}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "otheruser"
    assert body["id"] == str(other_user.id)


def test_read_user_by_username_not_found(client):
    """Test retrieving a nonexistent user returns 404."""
    resp = client.get("/api/v1/users/nonexistentuser")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "User not found"


# ==================== POST /{username}/follow tests ====================


def test_follow_user_success(client, current_user, other_user, db_session):
    """Test following a user successfully."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.post(f"/api/v1/users/{other_user.username}/follow")
    assert resp.status_code == 204

    # Verify follow relationship was created
    follow = db_session.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id == other_user.id
    ).first()
    assert follow is not None


def test_follow_user_not_found(client, current_user):
    """Test following a nonexistent user returns 404."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.post("/api/v1/users/nonexistentuser/follow")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "User not found"


def test_follow_yourself_returns_400(client, current_user):
    """Test that following yourself returns 400."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.post(f"/api/v1/users/{current_user.username}/follow")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Cannot follow yourself"


def test_follow_already_following_returns_400(client, current_user, other_user, db_session):
    """Test that following an already-followed user returns 400."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # Create initial follow
    follow = Follow(follower_id=current_user.id, following_id=other_user.id)
    db_session.add(follow)
    db_session.commit()

    # Try to follow again
    resp = client.post(f"/api/v1/users/{other_user.username}/follow")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Already following this user"


def test_follow_no_auth_returns_403(client, other_user):
    """Test that POST /follow returns 403 without auth."""
    resp = client.post(f"/api/v1/users/{other_user.username}/follow")
    assert resp.status_code == 403


# ==================== DELETE /{username}/follow tests ====================


def test_unfollow_user_success(client, current_user, other_user, db_session):
    """Test unfollowing a user successfully."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # Create initial follow
    follow = Follow(follower_id=current_user.id, following_id=other_user.id)
    db_session.add(follow)
    db_session.commit()

    # Unfollow
    resp = client.delete(f"/api/v1/users/{other_user.username}/follow")
    assert resp.status_code == 204


# ==================== DELETE /me tests ====================


def test_delete_current_user_anonymizes_and_removes_edges(client, current_user, other_user, db_session):
    """Deleting a user should anonymize their profile and remove follow/like edges."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # Create a playlist so we can assert stable ID references don't explode.
    playlist = Playlist(title="t", description=None, privacy="public", user_id=current_user.id)
    db_session.add(playlist)

    # Create like + follow edges
    db_session.add(Like(user_id=current_user.id, playlist_id=1))
    db_session.add(Follow(follower_id=current_user.id, following_id=other_user.id))
    db_session.add(Follow(follower_id=other_user.id, following_id=current_user.id))
    db_session.commit()

    resp = client.delete("/api/v1/users/me")
    assert resp.status_code == 204

    # User row still exists (stable internal ID)
    refreshed = db_session.query(User).filter(User.id == current_user.id).first()
    assert refreshed is not None
    assert refreshed.is_deleted is True
    assert refreshed.bio is None
    assert refreshed.avatar_url is None
    assert refreshed.username.startswith("deleted-user-")

    # Likes and follows are removed
    assert db_session.query(Like).filter(Like.user_id == current_user.id).count() == 0
    assert db_session.query(Follow).filter(Follow.follower_id == current_user.id).count() == 0
    assert db_session.query(Follow).filter(Follow.following_id == current_user.id).count() == 0

    # Profile becomes inaccessible by username
    resp2 = client.get(f"/api/v1/users/{refreshed.username}")
    assert resp2.status_code == 404
    assert resp2.json()["detail"] == "User not found"

    # Verify follow was deleted
    follow = db_session.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id == other_user.id
    ).first()
    assert follow is None


def test_unfollow_user_not_found(client, current_user):
    """Test unfollowing a nonexistent user returns 404."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.delete("/api/v1/users/nonexistentuser/follow")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "User not found"


def test_unfollow_not_following_returns_400(client, current_user, other_user):
    """Test unfollowing a user you don't follow returns 400."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.delete(f"/api/v1/users/{other_user.username}/follow")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Not following this user"


def test_unfollow_no_auth_returns_403(client, other_user):
    """Test that DELETE /follow returns 403 without auth."""
    resp = client.delete(f"/api/v1/users/{other_user.username}/follow")
    assert resp.status_code == 403


# ==================== GET /{username}/followers tests ====================


def test_get_user_followers_empty(client, other_user):
    """Test getting followers when user has no followers."""
    resp = client.get(f"/api/v1/users/{other_user.username}/followers")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_user_followers_success(client, other_user, current_user, third_user, db_session):
    """Test getting a user's followers."""
    # Create two follows: current_user and third_user follow other_user
    follow1 = Follow(follower_id=current_user.id, following_id=other_user.id)
    follow2 = Follow(follower_id=third_user.id, following_id=other_user.id)
    db_session.add(follow1)
    db_session.add(follow2)
    db_session.commit()

    resp = client.get(f"/api/v1/users/{other_user.username}/followers")
    assert resp.status_code == 200
    followers = resp.json()
    assert len(followers) == 2
    follower_usernames = {f["username"] for f in followers}
    assert follower_usernames == {"currentuser", "thirduser"}


def test_get_user_followers_not_found(client):
    """Test getting followers for a nonexistent user returns 404."""
    resp = client.get("/api/v1/users/nonexistentuser/followers")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "User not found"


# ==================== GET /{username}/following tests ====================


def test_get_user_following_empty(client, current_user):
    """Test getting following list when user follows nobody."""
    resp = client.get(f"/api/v1/users/{current_user.username}/following")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_user_following_success(client, current_user, other_user, third_user, db_session):
    """Test getting a user's following list."""
    # current_user follows both other_user and third_user
    follow1 = Follow(follower_id=current_user.id, following_id=other_user.id)
    follow2 = Follow(follower_id=current_user.id, following_id=third_user.id)
    db_session.add(follow1)
    db_session.add(follow2)
    db_session.commit()

    resp = client.get(f"/api/v1/users/{current_user.username}/following")
    assert resp.status_code == 200
    following = resp.json()
    assert len(following) == 2
    following_usernames = {f["username"] for f in following}
    assert following_usernames == {"otheruser", "thirduser"}


def test_get_user_following_not_found(client):
    """Test getting following list for a nonexistent user returns 404."""
    resp = client.get("/api/v1/users/nonexistentuser/following")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "User not found"


# ==================== Integration tests ====================


def test_follow_unfollow_cycle(client, current_user, other_user, db_session):
    """Test the full cycle: follow -> verify -> unfollow -> verify."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # Follow
    resp = client.post(f"/api/v1/users/{other_user.username}/follow")
    assert resp.status_code == 204

    # Verify follow exists
    resp = client.get(f"/api/v1/users/{other_user.username}/followers")
    assert len(resp.json()) == 1

    # Unfollow
    resp = client.delete(f"/api/v1/users/{other_user.username}/follow")
    assert resp.status_code == 204

    # Verify follow is gone
    resp = client.get(f"/api/v1/users/{other_user.username}/followers")
    assert len(resp.json()) == 0


def test_bidirectional_follows(client, current_user, other_user, db_session):
    """Test that A following B and B following A are independent."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # current_user follows other_user
    resp = client.post(f"/api/v1/users/{other_user.username}/follow")
    assert resp.status_code == 204

    # other_user follows current_user (manually in DB)
    follow = Follow(follower_id=other_user.id, following_id=current_user.id)
    db_session.add(follow)
    db_session.commit()

    # Verify both relationships exist
    resp = client.get(f"/api/v1/users/{other_user.username}/followers")
    assert len(resp.json()) == 1

    resp = client.get(f"/api/v1/users/{current_user.username}/followers")
    assert len(resp.json()) == 1
