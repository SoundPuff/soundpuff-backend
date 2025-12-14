import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base_class import Base
from app.models import User, Song, Playlist, Like, Comment
from app.db.session import get_db
from app.core.deps import get_current_user, get_current_user_optional


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"  # in-memory for tests
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)


def setup_module(module):
    # Create tables
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)


def get_test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_fixtures(suffix: str = None):
    db = TestingSessionLocal()
    # Create a user with unique username
    uname = f"testuser_{suffix or uuid.uuid4().hex[:8]}"
    user = User(id=uuid.uuid4(), username=uname)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create a song
    song = Song(title="Test Song", artist="Artist", song_url="http://example.com/song.mp3")
    db.add(song)
    db.commit()
    db.refresh(song)

    # Create a playlist owned by user
    playlist = Playlist(title="My Playlist", description="desc", user_id=user.id)
    db.add(playlist)
    db.commit()
    db.refresh(playlist)

    db.close()
    return user, song, playlist


# ==================== PLAYLIST CRUD TESTS ====================

def test_create_playlist():
    """Test creating a new playlist"""
    user, _, _ = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.post(
        "/api/v1/playlists/",
        json={"title": "New Playlist", "description": "Test description", "privacy": "public"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Playlist"
    assert data["description"] == "Test description"
    assert data["privacy"] == "public"
    assert data["user_id"] == str(user.id)
    
    # Cleanup
    app.dependency_overrides.clear()


def test_create_playlist_private():
    """Test creating a private playlist"""
    user, _, _ = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.post(
        "/api/v1/playlists/",
        json={"title": "Private Playlist", "description": "Secret", "privacy": "private"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["privacy"] == "private"
    
    # Cleanup
    app.dependency_overrides.clear()


def test_read_playlists_public():
    """Test getting public playlists without auth"""
    user, _, playlist = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user_optional] = lambda: None
    
    response = client.get("/api/v1/playlists/")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Cleanup
    app.dependency_overrides.clear()


def test_read_playlist_by_id():
    """Test getting specific playlist by ID"""
    user, _, playlist = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user_optional] = lambda: user
    
    response = client.get(f"/api/v1/playlists/{playlist.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == playlist.id
    assert data["title"] == "My Playlist"
    
    # Cleanup
    app.dependency_overrides.clear()


def test_read_playlist_not_found():
    """Test getting non-existent playlist"""
    user, _, _ = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user_optional] = lambda: user
    
    response = client.get("/api/v1/playlists/99999")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Playlist not found"
    
    # Cleanup
    app.dependency_overrides.clear()


def test_read_private_playlist_unauthorized():
    """Test accessing private playlist as non-owner"""
    owner, _, _ = create_fixtures()
    
    # Create private playlist
    db = TestingSessionLocal()
    private_playlist = Playlist(
        title="Private",
        description="Secret",
        user_id=owner.id,
        privacy="private"
    )
    db.add(private_playlist)
    db.commit()
    db.refresh(private_playlist)
    playlist_id = private_playlist.id
    db.close()
    
    # Try to access as different user (no auth)
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user_optional] = lambda: None
    
    response = client.get(f"/api/v1/playlists/{playlist_id}")
    
    assert response.status_code == 403
    assert "private" in response.json()["detail"].lower()
    
    # Cleanup
    app.dependency_overrides.clear()


def test_update_playlist():
    """Test updating playlist"""
    user, _, playlist = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.put(
        f"/api/v1/playlists/{playlist.id}",
        json={"title": "Updated Title", "description": "Updated desc"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["description"] == "Updated desc"
    
    # Cleanup
    app.dependency_overrides.clear()


def test_update_playlist_not_owner():
    """Test updating playlist as non-owner"""
    owner, _, playlist = create_fixtures()
    
    # Create another user
    other_user = User(id=uuid.uuid4(), username=f"other_{uuid.uuid4().hex[:8]}")
    db = TestingSessionLocal()
    db.add(other_user)
    db.commit()
    db.refresh(other_user)
    db.close()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: other_user
    
    response = client.put(
        f"/api/v1/playlists/{playlist.id}",
        json={"title": "Hacked"}
    )
    
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]
    
    # Cleanup
    app.dependency_overrides.clear()


def test_delete_playlist():
    """Test deleting playlist"""
    user, _, playlist = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.delete(f"/api/v1/playlists/{playlist.id}")
    
    assert response.status_code == 204
    
    # Verify it's deleted
    response2 = client.get(f"/api/v1/playlists/{playlist.id}")
    assert response2.status_code == 404
    
    # Cleanup
    app.dependency_overrides.clear()


def test_delete_playlist_not_owner():
    """Test deleting playlist as non-owner"""
    owner, _, playlist = create_fixtures()
    
    # Create another user
    other_user = User(id=uuid.uuid4(), username=f"other_{uuid.uuid4().hex[:8]}")
    db = TestingSessionLocal()
    db.add(other_user)
    db.commit()
    db.refresh(other_user)
    db.close()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: other_user
    
    response = client.delete(f"/api/v1/playlists/{playlist.id}")
    
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]
    
    # Cleanup
    app.dependency_overrides.clear()


# ==================== PLAYLIST SONGS TESTS ====================

def test_add_song_to_playlist_success():
    """Test adding song to playlist"""
    user, song, playlist = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.post(f"/api/v1/playlists/{playlist.id}/songs", json={"song_id": song.id})
    
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == playlist.id
    assert len(data["songs"]) == 1
    assert data["songs"][0]["id"] == song.id
    
    # Cleanup
    app.dependency_overrides.clear()


def test_add_song_already_in_playlist():
    """Test adding duplicate song to playlist"""
    user, song, playlist = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    # Add the song once
    client.post(f"/api/v1/playlists/{playlist.id}/songs", json={"song_id": song.id})
    
    # Try to add again
    response = client.post(f"/api/v1/playlists/{playlist.id}/songs", json={"song_id": song.id})
    
    assert response.status_code == 400
    assert "Song already in playlist" in response.json()["detail"]
    
    # Cleanup
    app.dependency_overrides.clear()


def test_add_song_unauthorized():
    """Test adding song as non-owner"""
    owner, song, playlist = create_fixtures()
    
    # Create another user
    other_user = User(id=uuid.uuid4(), username=f"other_{uuid.uuid4().hex[:8]}")
    db = TestingSessionLocal()
    db.add(other_user)
    db.commit()
    db.refresh(other_user)
    db.close()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: other_user
    
    response = client.post(f"/api/v1/playlists/{playlist.id}/songs", json={"song_id": song.id})
    
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]
    
    # Cleanup
    app.dependency_overrides.clear()


def test_add_nonexistent_song_to_playlist():
    """Test adding non-existent song to playlist"""
    user, _, playlist = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.post(f"/api/v1/playlists/{playlist.id}/songs", json={"song_id": 99999})
    
    assert response.status_code == 404
    assert "Song not found" in response.json()["detail"]
    
    # Cleanup
    app.dependency_overrides.clear()


def test_add_song_to_nonexistent_playlist():
    """Test adding song to non-existent playlist"""
    user, song, _ = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.post("/api/v1/playlists/99999/songs", json={"song_id": song.id})
    
    assert response.status_code == 404
    assert "Playlist not found" in response.json()["detail"]
    
    # Cleanup
    app.dependency_overrides.clear()


# ==================== PLAYLIST LIKES TESTS ====================

def test_like_playlist():
    """Test liking a playlist"""
    user, _, playlist = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.post(f"/api/v1/playlists/{playlist.id}/like")
    
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == str(user.id)
    assert data["playlist_id"] == playlist.id
    
    # Cleanup
    app.dependency_overrides.clear()


def test_like_playlist_already_liked():
    """Test liking an already liked playlist"""
    user, _, playlist = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    # Like first time
    client.post(f"/api/v1/playlists/{playlist.id}/like")
    
    # Try to like again
    response = client.post(f"/api/v1/playlists/{playlist.id}/like")
    
    assert response.status_code == 400
    assert "Already liked" in response.json()["detail"]
    
    # Cleanup
    app.dependency_overrides.clear()


def test_unlike_playlist():
    """Test unliking a playlist"""
    user, _, playlist = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    # Like first
    client.post(f"/api/v1/playlists/{playlist.id}/like")
    
    # Unlike
    response = client.delete(f"/api/v1/playlists/{playlist.id}/like")
    
    assert response.status_code == 204
    
    # Cleanup
    app.dependency_overrides.clear()


def test_unlike_playlist_not_liked():
    """Test unliking a playlist that wasn't liked"""
    user, _, playlist = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.delete(f"/api/v1/playlists/{playlist.id}/like")
    
    assert response.status_code == 404
    assert "Like not found" in response.json()["detail"]
    
    # Cleanup
    app.dependency_overrides.clear()


# ==================== PLAYLIST COMMENTS TESTS ====================

def test_create_comment():
    """Test creating a comment on a playlist"""
    user, _, playlist = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.post(
        f"/api/v1/playlists/{playlist.id}/comments",
        json={"body": "Great playlist!"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["body"] == "Great playlist!"
    assert data["user_id"] == str(user.id)
    assert data["playlist_id"] == playlist.id
    
    # Cleanup
    app.dependency_overrides.clear()


def test_read_playlist_comments():
    """Test reading comments on a playlist"""
    user, _, playlist = create_fixtures()
    
    # Create a comment
    db = TestingSessionLocal()
    comment = Comment(body="Test comment", user_id=user.id, playlist_id=playlist.id)
    db.add(comment)
    db.commit()
    db.close()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user_optional] = lambda: user
    
    response = client.get(f"/api/v1/playlists/{playlist.id}/comments")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["body"] == "Test comment"
    
    # Cleanup
    app.dependency_overrides.clear()


def test_update_comment():
    """Test updating a comment"""
    user, _, playlist = create_fixtures()
    
    # Create a comment
    db = TestingSessionLocal()
    comment = Comment(body="Original text", user_id=user.id, playlist_id=playlist.id)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment_id = comment.id
    db.close()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.put(
        f"/api/v1/playlists/comments/{comment_id}",
        json={"body": "Updated text"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["body"] == "Updated text"
    
    # Cleanup
    app.dependency_overrides.clear()


def test_update_comment_not_owner():
    """Test updating comment as non-owner"""
    owner, _, playlist = create_fixtures()
    
    # Create a comment
    db = TestingSessionLocal()
    comment = Comment(body="Original text", user_id=owner.id, playlist_id=playlist.id)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment_id = comment.id
    
    # Create another user
    other_user = User(id=uuid.uuid4(), username=f"other_{uuid.uuid4().hex[:8]}")
    db.add(other_user)
    db.commit()
    db.refresh(other_user)
    db.close()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: other_user
    
    response = client.put(
        f"/api/v1/playlists/comments/{comment_id}",
        json={"body": "Hacked"}
    )
    
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]
    
    # Cleanup
    app.dependency_overrides.clear()


def test_delete_comment():
    """Test deleting a comment"""
    user, _, playlist = create_fixtures()
    
    # Create a comment
    db = TestingSessionLocal()
    comment = Comment(body="Test comment", user_id=user.id, playlist_id=playlist.id)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment_id = comment.id
    db.close()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.delete(f"/api/v1/playlists/comments/{comment_id}")
    
    assert response.status_code == 204
    
    # Cleanup
    app.dependency_overrides.clear()


def test_delete_comment_not_owner():
    """Test deleting comment as non-owner"""
    owner, _, playlist = create_fixtures()
    
    # Create a comment
    db = TestingSessionLocal()
    comment = Comment(body="Test comment", user_id=owner.id, playlist_id=playlist.id)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment_id = comment.id
    
    # Create another user
    other_user = User(id=uuid.uuid4(), username=f"other_{uuid.uuid4().hex[:8]}")
    db.add(other_user)
    db.commit()
    db.refresh(other_user)
    db.close()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: other_user
    
    response = client.delete(f"/api/v1/playlists/comments/{comment_id}")
    
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]
    
    # Cleanup
    app.dependency_overrides.clear()


# ==================== PLAYLIST FEED TESTS ====================

def test_read_feed_empty():
    """Test reading feed when not following anyone"""
    user, _, _ = create_fixtures()
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: user
    
    response = client.get("/api/v1/playlists/feed")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
    
    # Cleanup
    app.dependency_overrides.clear()
