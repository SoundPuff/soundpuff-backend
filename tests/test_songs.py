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