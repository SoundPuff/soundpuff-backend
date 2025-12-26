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
from app.models import User, Song, Playlist, Like, Comment


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
def berra_user(db_session):
    user = User(id=uuid.uuid4(), username="berra", bio="a cool user")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def hit_em_up(db_session, berra_user):
    song = Song(title="Hit 'Em Up", artist="Berra Beats", song_url="http://example.com/hit.mp3")
    db_session.add(song)
    db_session.commit()
    db_session.refresh(song)
    return song


@pytest.fixture
def elif_playlist(db_session, berra_user):
    playlist = Playlist(title="elif", description="the elif playlist", privacy="public", user_id=berra_user.id)
    db_session.add(playlist)
    db_session.commit()
    db_session.refresh(playlist)
    return playlist


# ==================== SONG SEARCH ====================

def test_search_songs_requires_auth(client):
    resp = client.get("/api/v1/songs/search?query=hit")
    assert resp.status_code == 403


def test_search_songs_matches_title(client, berra_user, hit_em_up):
    app.dependency_overrides[get_current_user] = lambda: berra_user

    resp = client.get("/api/v1/songs/search?query=Hit")
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "Hit"
    assert body["total"] == 1
    assert body["songs"][0]["song"]["title"] == "Hit 'Em Up"


def test_search_songs_matches_artist(client, berra_user, hit_em_up):
    app.dependency_overrides[get_current_user] = lambda: berra_user

    resp = client.get("/api/v1/songs/search?query=Berra")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["songs"][0]["song"]["artist"] == "Berra Beats"


def test_search_songs_matches_id(client, berra_user, hit_em_up):
    app.dependency_overrides[get_current_user] = lambda: berra_user

    resp = client.get(f"/api/v1/songs/search?query={hit_em_up.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["songs"][0]["song"]["id"] == hit_em_up.id


def test_search_songs_pagination(client, berra_user, db_session):
    app.dependency_overrides[get_current_user] = lambda: berra_user

    # create several songs matching 'beat'
    for i in range(3):
        s = Song(title=f"Beat {i}", artist="Some Artist", song_url=f"http://example.com/beat{i}.mp3")
        db_session.add(s)
    db_session.commit()

    resp = client.get("/api/v1/songs/search?query=Beat&limit=1&offset=1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 3
    assert len(body["songs"]) == 1


# ==================== USER SEARCH ====================

def test_search_users_matches_username(client, berra_user):
    app.dependency_overrides[get_current_user] = lambda: berra_user

    resp = client.get("/api/v1/songs/users/search?query=berr")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    usernames = [u["user"]["username"] for u in body["users"]]
    assert "berra" in usernames


# ==================== PLAYLIST SEARCH ====================

def test_search_playlists_matches_title(client, berra_user, elif_playlist):
    app.dependency_overrides[get_current_user] = lambda: berra_user

    resp = client.get("/api/v1/songs/playlists/search?query=elif")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    titles = [p["playlist"]["title"] for p in body["playlists"]]
    assert "elif" in titles


def test_search_playlists_filters_private_to_owner(client, berra_user, elif_playlist, db_session):
    """Owner should see their private playlists while others remain hidden."""
    app.dependency_overrides[get_current_user] = lambda: berra_user

    # Private playlist owned by current user
    private_owned = Playlist(title="secret", description=None, privacy="private", user_id=berra_user.id)
    db_session.add(private_owned)

    # Private playlist owned by someone else should not appear
    stranger = User(id=uuid.uuid4(), username="stranger")
    db_session.add(stranger)
    private_foreign = Playlist(title="hidden", description=None, privacy="private", user_id=stranger.id)
    db_session.add(private_foreign)
    db_session.commit()

    db_session.add(Like(user_id=berra_user.id, playlist_id=private_owned.id))
    db_session.commit()

    resp = client.get("/api/v1/songs/playlists/search?query=secret")
    assert resp.status_code == 200
    playlists = resp.json()["playlists"]

    # Only own private playlist should be returned
    assert len(playlists) == 1
    item = playlists[0]["playlist"]
    assert item["id"] == private_owned.id
    assert item["privacy"] == "private"

    # Ensure stranger's private playlist was excluded
    assert all(p["playlist"]["id"] != private_foreign.id for p in playlists)


def test_search_playlists_includes_counts(client, berra_user, elif_playlist, db_session):
    """Test that playlist search response includes likes_count and comments_count."""
    app.dependency_overrides[get_current_user] = lambda: berra_user

    # Add a like and comment
    like = Like(user_id=berra_user.id, playlist_id=elif_playlist.id)
    db_session.add(like)
    comment = Comment(body="Test comment", user_id=berra_user.id, playlist_id=elif_playlist.id)
    db_session.add(comment)
    db_session.commit()

    resp = client.get("/api/v1/songs/playlists/search?query=elif")
    assert resp.status_code == 200
    body = resp.json()
    
    # Find the playlist in the results
    p = next(p["playlist"] for p in body["playlists"] if p["playlist"]["id"] == elif_playlist.id)
    assert p["likes_count"] == 1
    assert p["comments_count"] == 1


# ==================== COMBINED SEARCH ====================

def test_combined_search_returns_all_types(client, berra_user, hit_em_up, elif_playlist):
    app.dependency_overrides[get_current_user] = lambda: berra_user

    resp = client.get("/api/v1/songs/all?query=Hit&type=all")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_songs"] >= 1
    assert any(s["song"]["title"] == "Hit 'Em Up" for s in body["songs"]) 

    # filter only playlists
    resp2 = client.get("/api/v1/songs/all?query=elif&type=playlists")
    assert resp2.status_code == 200
    b2 = resp2.json()
    assert b2["total_playlists"] >= 1
    assert any(p["playlist"]["title"] == "elif" for p in b2["playlists"])


def test_combined_search_excludes_private_playlists_of_others(client, berra_user, db_session):
    app.dependency_overrides[get_current_user] = lambda: berra_user

    # Own private playlist should be visible
    own_private = Playlist(title="own secret", description=None, privacy="private", user_id=berra_user.id)
    db_session.add(own_private)

    # Other user's private playlist should be hidden
    stranger = User(id=uuid.uuid4(), username="stranger2")
    db_session.add(stranger)
    foreign_private = Playlist(title="stranger secret", description=None, privacy="private", user_id=stranger.id)
    db_session.add(foreign_private)
    db_session.commit()

    resp = client.get("/api/v1/songs/all?query=secret&type=playlists")
    assert resp.status_code == 200
    body = resp.json()

    titles = {p["playlist"]["title"] for p in body["playlists"]}
    assert "own secret" in titles
    assert "stranger secret" not in titles


# ==================== SONG LIKES ====================

def test_like_song_success(client, berra_user, hit_em_up, db_session):
    from app.core.deps import get_current_user
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: berra_user

    resp = client.post(f"/api/v1/songs/{hit_em_up.id}/like")
    assert resp.status_code == 201
    body = resp.json()
    assert body["song_id"] == hit_em_up.id
    assert body["user_id"] == str(berra_user.id)


def test_like_song_already_liked(client, berra_user, hit_em_up, db_session):
    from app.core.deps import get_current_user
    from app.main import app
    from app.models import SongLike
    app.dependency_overrides[get_current_user] = lambda: berra_user

    # Pre-like
    like = SongLike(user_id=berra_user.id, song_id=hit_em_up.id)
    db_session.add(like)
    db_session.commit()

    resp = client.post(f"/api/v1/songs/{hit_em_up.id}/like")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Already liked this song"


def test_unlike_song_success(client, berra_user, hit_em_up, db_session):
    from app.core.deps import get_current_user
    from app.main import app
    from app.models import SongLike
    app.dependency_overrides[get_current_user] = lambda: berra_user

    # Pre-like
    like = SongLike(user_id=berra_user.id, song_id=hit_em_up.id)
    db_session.add(like)
    db_session.commit()

    resp = client.delete(f"/api/v1/songs/{hit_em_up.id}/like")
    assert resp.status_code == 204

    # Verify deleted
    exists = db_session.query(SongLike).filter_by(user_id=berra_user.id, song_id=hit_em_up.id).first()
    assert exists is None


def test_unlike_song_not_found(client, berra_user, hit_em_up):
    from app.core.deps import get_current_user
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: berra_user

    resp = client.delete(f"/api/v1/songs/{hit_em_up.id}/like")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Like not found"


def test_song_search_includes_like_metadata(client, berra_user, hit_em_up, db_session):
    from app.core.deps import get_current_user
    from app.main import app
    from app.models import SongLike
    app.dependency_overrides[get_current_user] = lambda: berra_user

    # Add a like
    like = SongLike(user_id=berra_user.id, song_id=hit_em_up.id)
    db_session.add(like)
    db_session.commit()

    resp = client.get(f"/api/v1/songs/search?query={hit_em_up.title}")
    assert resp.status_code == 200
    body = resp.json()
    
    song_data = body["songs"][0]["song"]
    assert song_data["likes_count"] == 1
    # is_liked should not be returned in search results as per new requirement
    assert "is_liked" not in song_data
