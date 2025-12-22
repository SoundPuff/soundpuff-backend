import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base_class import Base
from app.db.session import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.models import User, Playlist, Song, Like, Comment, Follow


# Track next IDs for BigInteger primary keys in SQLite
_next_playlist_id = 1
_next_song_id = 1


def _get_next_playlist_id():
    """Get next playlist ID for manual assignment in SQLite."""
    global _next_playlist_id
    result = _next_playlist_id
    _next_playlist_id += 1
    return result


def _get_next_song_id():
    """Get next song ID for manual assignment in SQLite."""
    global _next_song_id
    result = _next_song_id
    _next_song_id += 1
    return result


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
    """Create the authenticated user."""
    user = User(id=uuid.uuid4(), username="playlistuser")
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_user(db_session):
    """Create another user."""
    user = User(id=uuid.uuid4(), username="otherplaylistuser")
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_song(db_session):
    """Create a test song."""
    song = Song(id=_get_next_song_id(), title="Test Song", artist="Test Artist", song_url="http://example.com/song.mp3")
    db_session.add(song)
    db_session.flush()
    db_session.refresh(song)
    return song


@pytest.fixture
def another_song(db_session):
    """Create another test song."""
    song = Song(id=_get_next_song_id(), title="Another Song", artist="Another Artist", song_url="http://example.com/song2.mp3")
    db_session.add(song)
    db_session.flush()
    db_session.refresh(song)
    return song


def _create_playlist(db_session, user, title, description="", privacy="public"):
    """Helper to create a playlist and ensure it gets an ID."""
    playlist = Playlist(
        id=_get_next_playlist_id(),
        title=title,
        description=description,
        privacy=privacy,
        user_id=user.id
    )
    db_session.add(playlist)
    db_session.flush()
    db_session.refresh(playlist)
    return playlist


@pytest.fixture
def public_playlist(db_session, current_user):
    """Create a public playlist owned by current_user."""
    return _create_playlist(db_session, current_user, "Public Playlist", "A public playlist", "public")


@pytest.fixture
def private_playlist(db_session, current_user):
    """Create a private playlist owned by current_user."""
    return _create_playlist(db_session, current_user, "Private Playlist", "A private playlist", "private")


@pytest.fixture
def other_public_playlist(db_session, other_user):
    """Create a public playlist owned by other_user."""
    return _create_playlist(db_session, other_user, "Other Public Playlist", "Someone else's public", "public")


# ==================== GET / (list playlists) tests ====================


def test_list_playlists_public_only_unauthenticated(client, public_playlist, private_playlist):
    """Unauthenticated users see only public playlists."""
    resp = client.get("/api/v1/playlists/")
    assert resp.status_code == 200
    playlists = resp.json()
    assert len(playlists) == 1
    assert playlists[0]["title"] == "Public Playlist"


def test_list_playlists_public_and_own_authenticated(client, current_user, public_playlist, private_playlist):
    """Authenticated users see public playlists and their own."""
    app.dependency_overrides[get_current_user_optional] = lambda: current_user

    resp = client.get("/api/v1/playlists/")
    assert resp.status_code == 200
    playlists = resp.json()
    assert len(playlists) == 2
    titles = {p["title"] for p in playlists}
    assert titles == {"Public Playlist", "Private Playlist"}


def test_list_playlists_includes_counts(client, current_user, public_playlist, db_session):
    """Test that playlist list response includes likes_count and comments_count."""
    app.dependency_overrides[get_current_user_optional] = lambda: current_user

    # Add a like and comment
    like = Like(user_id=current_user.id, playlist_id=public_playlist.id)
    db_session.add(like)
    comment = Comment(body="Test comment", user_id=current_user.id, playlist_id=public_playlist.id)
    db_session.add(comment)
    db_session.commit()

    resp = client.get("/api/v1/playlists/")
    assert resp.status_code == 200
    playlists = resp.json()
    
    # Find the public playlist in the list
    p = next(p for p in playlists if p["id"] == public_playlist.id)
    assert p["likes_count"] == 1
    assert p["comments_count"] == 1


def test_playlist_owner_deleted_is_rendered_anonymized(client, other_user, db_session):
    """Playlist responses should display deleted owners as 'Deleted user'."""
    # Create playlist owned by other_user
    playlist = _create_playlist(db_session, other_user, "Owned By Deleted", "", "public")
    other_user.is_deleted = True
    other_user.bio = "should not leak"
    other_user.avatar_url = "https://example.com/avatar.png"
    db_session.commit()

    resp = client.get(f"/api/v1/playlists/{playlist.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["owner"]["username"] == "Deleted user"
    assert body["owner"]["bio"] is None
    assert body["owner"]["avatar_url"] is None


def test_comment_user_deleted_is_rendered_anonymized(client, public_playlist, other_user, db_session):
    """Comment responses should display deleted authors as 'Deleted user'."""
    # Create comment by other_user
    c = Comment(body="hello", user_id=other_user.id, playlist_id=public_playlist.id)
    db_session.add(c)
    db_session.commit()

    other_user.is_deleted = True
    other_user.bio = "should not leak"
    other_user.avatar_url = "https://example.com/avatar.png"
    db_session.commit()

    resp = client.get(f"/api/v1/playlists/{public_playlist.id}/comments")
    assert resp.status_code == 200
    comments = resp.json()
    assert len(comments) >= 1
    found = next(x for x in comments if x["id"] == c.id)
    assert found["user"]["username"] == "Deleted user"
    assert found["user"]["bio"] is None
    assert found["user"]["avatar_url"] is None


def test_list_playlists_pagination(client, current_user, db_session):
    """Test pagination with skip and limit."""
    app.dependency_overrides[get_current_user_optional] = lambda: current_user

    # Create 5 playlists
    for i in range(5):
        _create_playlist(db_session, current_user, f"Playlist {i}", "", "public")

    # Get first page (limit 2)
    resp = client.get("/api/v1/playlists/?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Get second page
    resp = client.get("/api/v1/playlists/?skip=2&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_boolean_privacy_is_normalized_to_private(client, db_session, current_user):
    """Legacy boolean False privacy should be normalized to 'private' in responses."""
    # Insert playlist with boolean False privacy directly in DB
    playlist = Playlist(
        id=_get_next_playlist_id(),
        title="Bool Privacy Private",
        description="boolean privacy false",
        privacy=False,
        user_id=current_user.id
    )
    db_session.add(playlist)
    db_session.flush()
    db_session.refresh(playlist)

    app.dependency_overrides[get_current_user_optional] = lambda: current_user
    resp = client.get("/api/v1/playlists/")
    assert resp.status_code == 200
    found = next((p for p in resp.json() if p["title"] == "Bool Privacy Private"), None)
    assert found is not None
    assert found["privacy"] == "private"


def test_boolean_privacy_is_normalized_to_public(client, db_session, current_user):
    """Legacy boolean True privacy should be normalized to 'public' in responses."""
    playlist = Playlist(
        id=_get_next_playlist_id(),
        title="Bool Privacy Public",
        description="boolean privacy true",
        privacy=True,
        user_id=current_user.id
    )
    db_session.add(playlist)
    db_session.flush()
    db_session.refresh(playlist)

    app.dependency_overrides[get_current_user_optional] = lambda: current_user
    resp = client.get("/api/v1/playlists/")
    assert resp.status_code == 200
    found = next((p for p in resp.json() if p["title"] == "Bool Privacy Public"), None)
    assert found is not None
    assert found["privacy"] == "public"


# ==================== GET /feed tests ====================


def test_read_feed_requires_auth(client):
    """Feed endpoint requires authentication."""
    resp = client.get("/api/v1/playlists/feed")
    assert resp.status_code == 403


def test_read_feed_empty_when_not_following(client, current_user, other_public_playlist):
    """Feed is empty when user doesn't follow anyone."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.get("/api/v1/playlists/feed")
    assert resp.status_code == 200
    assert resp.json() == []


def test_read_feed_shows_followed_user_playlists(client, current_user, other_user, other_public_playlist, db_session):
    """Feed shows public playlists from followed users."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # Follow other_user
    follow = Follow(follower_id=current_user.id, following_id=other_user.id)
    db_session.add(follow)
    db_session.commit()

    resp = client.get("/api/v1/playlists/feed")
    assert resp.status_code == 200
    playlists = resp.json()
    assert len(playlists) == 1
    assert playlists[0]["title"] == "Other Public Playlist"


def test_read_feed_doesnt_show_private_from_followed(client, current_user, other_user, db_session):
    """Feed doesn't show private playlists even from followed users."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # Create private playlist for other_user
    private = _create_playlist(db_session, other_user, "Private from Other", "", "private")

    # Follow other_user
    follow = Follow(follower_id=current_user.id, following_id=other_user.id)
    db_session.add(follow)
    db_session.commit()

    resp = client.get("/api/v1/playlists/feed")
    assert resp.status_code == 200
    assert resp.json() == []


# ==================== POST / (create playlist) tests ====================


def test_create_playlist_success(client, current_user, db_session):
    """Test creating a playlist successfully."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.post(
        "/api/v1/playlists/",
        json={"title": "New Playlist", "description": "A new playlist", "privacy": "public"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "New Playlist"
    assert body["description"] == "A new playlist"
    assert body["privacy"] == "public"

    # Verify in DB
    playlist = db_session.query(Playlist).filter(Playlist.title == "New Playlist").first()
    assert playlist is not None
    assert playlist.user_id == current_user.id


def test_create_playlist_default_privacy(client, current_user):
    """Test that playlist defaults to public privacy."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.post(
        "/api/v1/playlists/",
        json={"title": "Default Privacy Playlist"}
    )
    assert resp.status_code == 201
    assert resp.json()["privacy"] == "public"


def test_create_playlist_no_auth_returns_403(client):
    """Test that creating a playlist requires auth."""
    resp = client.post(
        "/api/v1/playlists/",
        json={"title": "Test"}
    )
    assert resp.status_code == 403


# ==================== GET /{playlist_id} tests ====================


def test_read_playlist_public_unauthenticated(client, public_playlist):
    """Unauthenticated users can read public playlists."""
    resp = client.get(f"/api/v1/playlists/{public_playlist.id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Public Playlist"


def test_read_playlist_private_unauthenticated_forbidden(client, private_playlist):
    """Unauthenticated users cannot read private playlists."""
    resp = client.get(f"/api/v1/playlists/{private_playlist.id}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Playlist not found"


def test_read_playlist_private_owner_can_read(client, current_user, private_playlist):
    """Owner can read their own private playlist."""
    app.dependency_overrides[get_current_user_optional] = lambda: current_user

    resp = client.get(f"/api/v1/playlists/{private_playlist.id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Private Playlist"


def test_read_playlist_private_non_owner_forbidden(client, current_user, other_user, db_session):
    """Non-owner cannot read someone else's private playlist."""
    app.dependency_overrides[get_current_user_optional] = lambda: current_user

    other_playlist = _create_playlist(db_session, other_user, "Someone Else's Private", "", "private")

    resp = client.get(f"/api/v1/playlists/{other_playlist.id}")
    assert resp.status_code == 404


def test_read_playlist_not_found(client):
    """Test reading nonexistent playlist returns 404."""
    resp = client.get("/api/v1/playlists/99999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Playlist not found"


def test_read_playlist_includes_counts(client, public_playlist, current_user, db_session):
    """Test that playlist response includes likes_count and comments_count."""
    app.dependency_overrides[get_current_user_optional] = lambda: current_user

    # Add a like and comment
    like = Like(user_id=current_user.id, playlist_id=public_playlist.id)
    db_session.add(like)
    comment = Comment(body="Test comment", user_id=current_user.id, playlist_id=public_playlist.id)
    db_session.add(comment)
    db_session.commit()

    resp = client.get(f"/api/v1/playlists/{public_playlist.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["likes_count"] == 1
    assert body["comments_count"] == 1


# ==================== PUT /{playlist_id} tests ====================


def test_update_playlist_success(client, current_user, public_playlist, db_session):
    """Test updating a playlist."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.put(
        f"/api/v1/playlists/{public_playlist.id}",
        json={"title": "Updated Title", "description": "Updated desc", "privacy": "private"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Updated Title"
    assert body["description"] == "Updated desc"
    assert body["privacy"] == "private"

    # Verify in DB
    playlist = db_session.query(Playlist).filter(Playlist.id == public_playlist.id).first()
    assert playlist.title == "Updated Title"


def test_update_playlist_partial(client, current_user, public_playlist):
    """Test partial update of playlist."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    original_description = public_playlist.description
    resp = client.put(
        f"/api/v1/playlists/{public_playlist.id}",
        json={"title": "New Title"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "New Title"
    assert body["description"] == original_description


def test_update_playlist_not_found(client, current_user):
    """Test updating nonexistent playlist returns 404."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.put(
        "/api/v1/playlists/99999",
        json={"title": "New Title"}
    )
    assert resp.status_code == 404


def test_update_playlist_not_owner(client, current_user, other_user, db_session):
    """Test that non-owner cannot update playlist."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    other_playlist = _create_playlist(db_session, other_user, "Other's Playlist")

    resp = client.put(
        f"/api/v1/playlists/{other_playlist.id}",
        json={"title": "Hacked"}
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Not authorized to update this playlist"


def test_update_playlist_no_auth(client, public_playlist):
    """Test that updating requires auth."""
    resp = client.put(
        f"/api/v1/playlists/{public_playlist.id}",
        json={"title": "New Title"}
    )
    assert resp.status_code == 403


# ==================== DELETE /{playlist_id} tests ====================


def test_delete_playlist_success(client, current_user, public_playlist, db_session):
    """Test deleting a playlist."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.delete(f"/api/v1/playlists/{public_playlist.id}")
    assert resp.status_code == 204

    # Verify deleted from DB
    playlist = db_session.query(Playlist).filter(Playlist.id == public_playlist.id).first()
    assert playlist is None


def test_delete_playlist_not_found(client, current_user):
    """Test deleting nonexistent playlist returns 404."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.delete("/api/v1/playlists/99999")
    assert resp.status_code == 404


def test_delete_playlist_not_owner(client, current_user, other_user, db_session):
    """Test that non-owner cannot delete playlist."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    other_playlist = _create_playlist(db_session, other_user, "Other's Playlist")

    resp = client.delete(f"/api/v1/playlists/{other_playlist.id}")
    assert resp.status_code == 403


def test_delete_playlist_no_auth(client, public_playlist):
    """Test that deleting requires auth."""
    resp = client.delete(f"/api/v1/playlists/{public_playlist.id}")
    assert resp.status_code == 403


# ==================== POST /{playlist_id}/like tests ====================


def test_like_playlist_success(client, current_user, public_playlist, db_session):
    """Test liking a playlist."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.post(f"/api/v1/playlists/{public_playlist.id}/like")
    assert resp.status_code == 201
    body = resp.json()
    assert body["user_id"] == str(current_user.id)
    assert body["playlist_id"] == public_playlist.id

    # Verify in DB
    like = db_session.query(Like).filter(
        Like.user_id == current_user.id,
        Like.playlist_id == public_playlist.id
    ).first()
    assert like is not None


def test_like_playlist_not_found(client, current_user):
    """Test liking nonexistent playlist returns 404."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.post("/api/v1/playlists/99999/like")
    assert resp.status_code == 404


def test_like_playlist_private_not_accessible(client, current_user, other_user, db_session):
    """Test that liking someone else's private playlist is forbidden."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    private = _create_playlist(db_session, other_user, "Private", "", "private")

    resp = client.post(f"/api/v1/playlists/{private.id}/like")
    assert resp.status_code == 404


def test_like_playlist_already_liked(client, current_user, public_playlist, db_session):
    """Test that liking same playlist twice returns error."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # Like once
    resp = client.post(f"/api/v1/playlists/{public_playlist.id}/like")
    assert resp.status_code == 201

    # Try to like again
    resp = client.post(f"/api/v1/playlists/{public_playlist.id}/like")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Already liked this playlist"


def test_like_playlist_no_auth(client, public_playlist):
    """Test that liking requires auth."""
    resp = client.post(f"/api/v1/playlists/{public_playlist.id}/like")
    assert resp.status_code == 403


# ==================== DELETE /{playlist_id}/like tests ====================


def test_unlike_playlist_success(client, current_user, public_playlist, db_session):
    """Test unliking a playlist."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # Like first
    like = Like(user_id=current_user.id, playlist_id=public_playlist.id)
    db_session.add(like)
    db_session.commit()

    # Unlike
    resp = client.delete(f"/api/v1/playlists/{public_playlist.id}/like")
    assert resp.status_code == 204

    # Verify deleted from DB
    like = db_session.query(Like).filter(
        Like.user_id == current_user.id,
        Like.playlist_id == public_playlist.id
    ).first()
    assert like is None


def test_unlike_playlist_not_liked(client, current_user, public_playlist):
    """Test unliking a playlist you didn't like returns 404."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.delete(f"/api/v1/playlists/{public_playlist.id}/like")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Like not found"


def test_unlike_playlist_no_auth(client, public_playlist):
    """Test that unliking requires auth."""
    resp = client.delete(f"/api/v1/playlists/{public_playlist.id}/like")
    assert resp.status_code == 403


# ==================== POST /{playlist_id}/songs tests ====================


def test_add_song_to_playlist_success(client, current_user, public_playlist, test_song, db_session):
    """Test adding a song to a playlist."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.post(
        f"/api/v1/playlists/{public_playlist.id}/songs",
        json={"song_id": test_song.id}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == public_playlist.id
    assert len(body["songs"]) == 1
    assert body["songs"][0]["id"] == test_song.id

    # Verify in DB
    playlist = db_session.query(Playlist).filter(Playlist.id == public_playlist.id).first()
    assert len(playlist.songs) == 1


def test_add_song_to_playlist_not_owner(client, current_user, other_user, db_session, test_song):
    """Test that non-owner cannot add songs."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    other_playlist = _create_playlist(db_session, other_user, "Other's Playlist")

    resp = client.post(
        f"/api/v1/playlists/{other_playlist.id}/songs",
        json={"song_id": test_song.id}
    )
    assert resp.status_code == 403


def test_add_song_to_playlist_song_not_found(client, current_user, public_playlist):
    """Test adding nonexistent song returns 404."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.post(
        f"/api/v1/playlists/{public_playlist.id}/songs",
        json={"song_id": 99999}
    )
    assert resp.status_code == 404


def test_add_song_to_playlist_duplicate(client, current_user, public_playlist, test_song, db_session):
    """Test adding same song twice returns error."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # Add song once
    resp = client.post(
        f"/api/v1/playlists/{public_playlist.id}/songs",
        json={"song_id": test_song.id}
    )
    assert resp.status_code == 201

    # Try to add again
    resp = client.post(
        f"/api/v1/playlists/{public_playlist.id}/songs",
        json={"song_id": test_song.id}
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Song already in playlist"


def test_add_song_playlist_not_found(client, current_user, test_song):
    """Test adding song to nonexistent playlist returns 404."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.post(
        "/api/v1/playlists/99999/songs",
        json={"song_id": test_song.id}
    )
    assert resp.status_code == 404


def test_add_song_no_auth(client, public_playlist, test_song):
    """Test that adding songs requires auth."""
    resp = client.post(
        f"/api/v1/playlists/{public_playlist.id}/songs",
        json={"song_id": test_song.id}
    )
    assert resp.status_code == 403


# ==================== DELETE /{playlist_id}/songs/{song_id} tests ====================


def test_remove_song_from_playlist_success(client, current_user, public_playlist, test_song, db_session):
    """Test removing a song from a playlist by owner."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # Add song to playlist first
    public_playlist.songs.append(test_song)
    db_session.commit()

    resp = client.delete(f"/api/v1/playlists/{public_playlist.id}/songs/{test_song.id}")
    assert resp.status_code == 204

    # Verify removed from DB
    playlist = db_session.query(Playlist).filter(Playlist.id == public_playlist.id).first()
    assert len(playlist.songs) == 0


def test_remove_song_from_playlist_not_owner(client, current_user, other_user, db_session, test_song):
    """Test that non-owner cannot remove songs."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    other_playlist = _create_playlist(db_session, other_user, "Other's Playlist")
    other_playlist.songs.append(test_song)
    db_session.commit()

    resp = client.delete(f"/api/v1/playlists/{other_playlist.id}/songs/{test_song.id}")
    assert resp.status_code == 403


def test_remove_song_not_in_playlist(client, current_user, public_playlist, test_song):
    """Test removing a song that isn't in the playlist returns 404."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.delete(f"/api/v1/playlists/{public_playlist.id}/songs/{test_song.id}")
    assert resp.status_code == 404


def test_remove_song_playlist_not_found(client, current_user, test_song):
    """Test removing a song from nonexistent playlist returns 404."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.delete(f"/api/v1/playlists/99999/songs/{test_song.id}")
    assert resp.status_code == 404


def test_remove_song_no_auth(client, public_playlist, test_song):
    """Test that removing songs requires auth."""
    resp = client.delete(f"/api/v1/playlists/{public_playlist.id}/songs/{test_song.id}")
    assert resp.status_code == 403


# ==================== GET /{playlist_id}/comments tests ====================


def test_get_playlist_comments_empty(client, public_playlist):
    """Test getting comments from playlist with no comments."""
    resp = client.get(f"/api/v1/playlists/{public_playlist.id}/comments")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_playlist_comments_success(client, current_user, public_playlist, db_session):
    """Test getting comments from a playlist."""
    # Add comments
    comment1 = Comment(body="First comment", user_id=current_user.id, playlist_id=public_playlist.id)
    comment2 = Comment(body="Second comment", user_id=current_user.id, playlist_id=public_playlist.id)
    db_session.add(comment1)
    db_session.add(comment2)
    db_session.commit()

    resp = client.get(f"/api/v1/playlists/{public_playlist.id}/comments")
    assert resp.status_code == 200
    comments = resp.json()
    assert len(comments) == 2
    bodies = {c["body"] for c in comments}
    assert bodies == {"First comment", "Second comment"}


def test_get_playlist_comments_private_unauthenticated(client, current_user, db_session):
    """Test getting comments from private playlist requires proper auth."""
    private = _create_playlist(db_session, current_user, "Private", "", "private")

    resp = client.get(f"/api/v1/playlists/{private.id}/comments")
    assert resp.status_code == 404


def test_get_playlist_comments_not_found(client):
    """Test getting comments from nonexistent playlist returns 404."""
    resp = client.get("/api/v1/playlists/99999/comments")
    assert resp.status_code == 404


# ==================== POST /{playlist_id}/comments tests ====================


def test_create_comment_success(client, current_user, public_playlist, db_session):
    """Test creating a comment on a playlist."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.post(
        f"/api/v1/playlists/{public_playlist.id}/comments",
        json={"body": "Great playlist!", "playlist_id": public_playlist.id}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["body"] == "Great playlist!"
    assert body["user_id"] == str(current_user.id)

    # Verify in DB
    comment = db_session.query(Comment).filter(Comment.body == "Great playlist!").first()
    assert comment is not None
    assert comment.playlist_id == public_playlist.id


def test_create_comment_private_playlist_owner(client, current_user, private_playlist):
    """Test creating comment on own private playlist."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.post(
        f"/api/v1/playlists/{private_playlist.id}/comments",
        json={"body": "My comment", "playlist_id": private_playlist.id}
    )
    assert resp.status_code == 201


def test_create_comment_private_playlist_non_owner(client, current_user, other_user, db_session):
    """Test creating comment on someone else's private playlist is forbidden."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    private = _create_playlist(db_session, other_user, "Private", "", "private")

    resp = client.post(
        f"/api/v1/playlists/{private.id}/comments",
        json={"body": "Hack attempt", "playlist_id": private.id}
    )
    assert resp.status_code == 404


def test_create_comment_playlist_not_found(client, current_user):
    """Test creating comment on nonexistent playlist returns 404."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.post(
        "/api/v1/playlists/99999/comments",
        json={"body": "test", "playlist_id": 99999}
    )
    assert resp.status_code == 404


def test_create_comment_no_auth(client, public_playlist):
    """Test that creating comment requires auth."""
    resp = client.post(
        f"/api/v1/playlists/{public_playlist.id}/comments",
        json={"body": "test"}
    )
    assert resp.status_code == 403


# ==================== PUT /comments/{comment_id} tests ====================


def test_update_comment_success(client, current_user, public_playlist, db_session):
    """Test updating a comment."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # Create comment
    comment = Comment(body="Original", user_id=current_user.id, playlist_id=public_playlist.id)
    db_session.add(comment)
    db_session.commit()

    # Update
    resp = client.put(
        f"/api/v1/playlists/comments/{comment.id}",
        json={"body": "Updated"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["body"] == "Updated"


def test_update_comment_not_owner(client, current_user, other_user, public_playlist, db_session):
    """Test that non-owner cannot update comment."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # Create comment by other_user
    comment = Comment(body="Original", user_id=other_user.id, playlist_id=public_playlist.id)
    db_session.add(comment)
    db_session.commit()

    resp = client.put(
        f"/api/v1/playlists/comments/{comment.id}",
        json={"body": "Hacked"}
    )
    assert resp.status_code == 403


def test_update_comment_not_found(client, current_user):
    """Test updating nonexistent comment returns 404."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.put(
        "/api/v1/playlists/comments/99999",
        json={"body": "test"}
    )
    assert resp.status_code == 404


def test_update_comment_no_auth(client, public_playlist, db_session):
    """Test that updating comment requires auth."""
    user = User(id=uuid.uuid4(), username="someuser")
    db_session.add(user)
    db_session.commit()

    comment = Comment(body="Original", user_id=user.id, playlist_id=public_playlist.id)
    db_session.add(comment)
    db_session.commit()

    resp = client.put(
        f"/api/v1/playlists/comments/{comment.id}",
        json={"body": "test"}
    )
    assert resp.status_code == 403


# ==================== DELETE /comments/{comment_id} tests ====================


def test_delete_comment_success(client, current_user, public_playlist, db_session):
    """Test deleting a comment."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # Create comment
    comment = Comment(body="To delete", user_id=current_user.id, playlist_id=public_playlist.id)
    db_session.add(comment)
    db_session.commit()

    # Delete
    resp = client.delete(f"/api/v1/playlists/comments/{comment.id}")
    assert resp.status_code == 204

    # Verify deleted
    deleted = db_session.query(Comment).filter(Comment.id == comment.id).first()
    assert deleted is None


def test_delete_comment_not_owner(client, current_user, other_user, public_playlist, db_session):
    """Test that non-owner cannot delete comment."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    # Create comment by other_user
    comment = Comment(body="Original", user_id=other_user.id, playlist_id=public_playlist.id)
    db_session.add(comment)
    db_session.commit()

    resp = client.delete(f"/api/v1/playlists/comments/{comment.id}")
    assert resp.status_code == 403


def test_delete_comment_not_found(client, current_user):
    """Test deleting nonexistent comment returns 404."""
    app.dependency_overrides[get_current_user] = lambda: current_user

    resp = client.delete("/api/v1/playlists/comments/99999")
    assert resp.status_code == 404


def test_delete_comment_no_auth(client, public_playlist, db_session):
    """Test that deleting comment requires auth."""
    user = User(id=uuid.uuid4(), username="someuser")
    db_session.add(user)
    db_session.commit()

    comment = Comment(body="Original", user_id=user.id, playlist_id=public_playlist.id)
    db_session.add(comment)
    db_session.commit()

    resp = client.delete(f"/api/v1/playlists/comments/{comment.id}")
    assert resp.status_code == 403
