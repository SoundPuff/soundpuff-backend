from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Song, User, Playlist, Like
from app.schemas.search import (
    SongSearchResult, 
    SongSearchResults,
    UserSearchResult,
    UserSearchResults,
    PlaylistSearchResult,
    PlaylistSearchResults,
    SearchResults,
    SearchType
)


router = APIRouter()


# ==================== HELPER FUNCTIONS ====================

def _check_user_liked_playlist(db: Session, playlist_id: int, user_id) -> bool:
    """Check if a user has liked a specific playlist."""
    if user_id is None:
        return False
    return (
        db.query(Like.playlist_id)
        .filter(Like.user_id == user_id, Like.playlist_id == playlist_id)
        .first()
        is not None
    )


def _bulk_playlist_counts(db: Session, playlist_ids: list[int]) -> dict[int, dict[str, int]]:
    """Return likes/comments counts keyed by playlist id."""
    if not playlist_ids:
        return {}

    likes_counts = dict(
        db.query(Like.playlist_id, func.count(Like.user_id))
        .filter(Like.playlist_id.in_(playlist_ids))
        .group_by(Like.playlist_id)
        .all()
    )
    comments_counts = dict(
        db.query(Comment.playlist_id, func.count(Comment.id))
        .filter(Comment.playlist_id.in_(playlist_ids))
        .group_by(Comment.playlist_id)
        .all()
    )

    return {
        pid: {
            "likes": likes_counts.get(pid, 0),
            "comments": comments_counts.get(pid, 0),
        }
        for pid in playlist_ids
    }


def _bulk_liked_playlist_ids(db: Session, playlist_ids: list[int], user_id: Optional[UUID]) -> set[int]:
    """Prefetch playlists liked by the user to avoid per-row lookups."""
    if not playlist_ids or user_id is None:
        return set()

    liked = db.query(Like.playlist_id).filter(
        Like.user_id == user_id,
        Like.playlist_id.in_(playlist_ids),
    )
    return {row[0] for row in liked.all()}


def _playlist_to_search_response(
    db: Session,
    playlist: Playlist,
    current_user: User,
    counts: Optional[dict[int, dict[str, int]]] = None,
    liked_playlist_ids: Optional[set[int]] = None,
) -> dict:
    """Convert a playlist model to a search response dict with is_liked."""
    playlist_counts = (counts or {}).get(playlist.id)
    likes_count = None if not playlist_counts else playlist_counts.get("likes", 0)
    comments_count = None if not playlist_counts else playlist_counts.get("comments", 0)

    if likes_count is None:
        likes_count = (
            db.query(func.count(Like.user_id))
            .filter(Like.playlist_id == playlist.id)
            .scalar()
            or 0
        )

    if comments_count is None:
        comments_count = (
            db.query(func.count(Comment.id))
            .filter(Comment.playlist_id == playlist.id)
            .scalar()
            or 0
        )

    is_liked = (
        playlist.id in liked_playlist_ids
        if liked_playlist_ids is not None
        else _check_user_liked_playlist(db, playlist.id, current_user.id)
    )
    
    return {
        "id": playlist.id,
        "title": playlist.title,
        "description": playlist.description,
        "privacy": playlist.privacy,
        "user_id": playlist.user_id,
        "created_at": playlist.created_at,
        "updated_at": playlist.updated_at,
        "owner": playlist.owner,
        "songs": playlist.songs,
        "likes_count": likes_count,
        "comments_count": comments_count,
        "is_liked": is_liked,
    }


# ==================== SONG SEARCH ====================

@router.get("/search", response_model=SongSearchResults)
def search_songs(
    query: str = Query(..., min_length=1, description="Search query for song title or artist"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search songs by title or artist using a case-insensitive partial match.
    Requires authentication.
    
    - **query**: Search term (e.g., "ar" matches "artist", "guitar", etc.)
    - **limit**: Maximum results to return (default: 20, max: 100)
    - **offset**: Pagination offset
    """

    search_filter = or_(
        Song.title.ilike(f"%{query}%"),
        Song.artist.ilike(f"%{query}%"),
    )

    base_query = db.query(Song).filter(search_filter)
    total = base_query.count()

    songs = (
        base_query.order_by(desc(Song.created_at)).offset(offset).limit(limit).all()
    )

    song_results = [SongSearchResult(song=song) for song in songs]

    return SongSearchResults(query=query, songs=song_results, total=total)


# ==================== USER SEARCH ====================

@router.get("/users/search", response_model=UserSearchResults)
def search_users(
    query: str = Query(..., min_length=1, description="Search query for username or bio"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search users by username or bio using a case-insensitive partial match.
    Requires authentication.
    
    - **query**: Search term (e.g., "ar" matches "arda", "ariana", etc.)
    - **limit**: Maximum results to return (default: 20, max: 100)
    - **offset**: Pagination offset
    """

    search_filter = or_(
        User.username.ilike(f"%{query}%"),
        User.bio.ilike(f"%{query}%"),
    )

    base_query = db.query(User).filter(search_filter)
    total = base_query.count()

    users = (
        base_query.order_by(desc(User.created_at)).offset(offset).limit(limit).all()
    )

    user_results = [UserSearchResult(user=user) for user in users]

    return UserSearchResults(query=query, users=user_results, total=total)


# ==================== PLAYLIST SEARCH ====================

@router.get("/playlists/search", response_model=PlaylistSearchResults)
def search_playlists(
    query: str = Query(..., min_length=1, description="Search query for playlist title or description"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search playlists by title or description using a case-insensitive partial match.
    Requires authentication. Returns public playlists and your own private playlists.
    
    - **query**: Search term (e.g., "rock" matches "Rock Classics", "Hard Rock", etc.)
    - **limit**: Maximum results to return (default: 20, max: 100)
    - **offset**: Pagination offset
    """

    search_filter = or_(
        Playlist.title.ilike(f"%{query}%"),
        Playlist.description.ilike(f"%{query}%"),
    )

    base_query = db.query(Playlist).options(
        selectinload(Playlist.owner),
        selectinload(Playlist.songs),
    ).filter(search_filter)

    # Show public + user's own private playlists
    base_query = base_query.filter(
        or_(
            Playlist.privacy == "public",
            Playlist.user_id == current_user.id
        )
    )

    total = base_query.count()

    playlists = base_query.order_by(desc(Playlist.created_at)).offset(offset).limit(limit).all()

    playlist_ids = [playlist.id for playlist in playlists]
    counts = _bulk_playlist_counts(db, playlist_ids)
    liked_ids = _bulk_liked_playlist_ids(db, playlist_ids, current_user.id)

    playlist_results = [
        PlaylistSearchResult(
            playlist=_playlist_to_search_response(db, playlist, current_user, counts, liked_ids)
        )
        for playlist in playlists
    ]

    return PlaylistSearchResults(query=query, playlists=playlist_results, total=total)


# ==================== COMBINED SEARCH ====================

@router.get("/all", response_model=SearchResults)
def search_all(
    query: str = Query(..., min_length=1, description="Search query"),
    type: SearchType = Query(SearchType.ALL, description="Type of search: all, users, songs, or playlists"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results per category"),
    offset: int = Query(0, ge=0, description="Number of results to skip per category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search across users, songs, and playlists at once.
    Requires authentication.
    
    - **query**: Search term (e.g., "ar" matches "arda", "artist", "guitar", etc.)
    - **type**: Filter by type - "all" returns all types, or specify "users", "songs", "playlists"
    - **limit**: Maximum results per category (default: 10, max: 50)
    - **offset**: Pagination offset per category
    """

    users = []
    songs = []
    playlists = []
    total_users = 0
    total_songs = 0
    total_playlists = 0

    # Search Users
    if type in (SearchType.ALL, SearchType.USERS):
        user_filter = or_(
            User.username.ilike(f"%{query}%"),
            User.bio.ilike(f"%{query}%"),
        )
        user_query = db.query(User).filter(user_filter)
        total_users = user_query.count()
        user_list = user_query.order_by(desc(User.created_at)).offset(offset).limit(limit).all()
        users = [UserSearchResult(user=user) for user in user_list]

    # Search Songs
    if type in (SearchType.ALL, SearchType.SONGS):
        song_filter = or_(
            Song.title.ilike(f"%{query}%"),
            Song.artist.ilike(f"%{query}%"),
        )
        song_query = db.query(Song).filter(song_filter)
        total_songs = song_query.count()
        song_list = song_query.order_by(desc(Song.created_at)).offset(offset).limit(limit).all()
        songs = [SongSearchResult(song=song) for song in song_list]

    # Search Playlists
    if type in (SearchType.ALL, SearchType.PLAYLISTS):
        playlist_filter = or_(
            Playlist.title.ilike(f"%{query}%"),
            Playlist.description.ilike(f"%{query}%"),
        )
        playlist_query = db.query(Playlist).options(
            selectinload(Playlist.owner),
            selectinload(Playlist.songs),
        ).filter(playlist_filter)
        
        # Show public + user's own private playlists
        playlist_query = playlist_query.filter(
            or_(
                Playlist.privacy == "public",
                Playlist.user_id == current_user.id
            )
        )
        
        total_playlists = playlist_query.count()
        playlist_list = playlist_query.order_by(desc(Playlist.created_at)).offset(offset).limit(limit).all()

        playlist_ids = [p.id for p in playlist_list]
        counts = _bulk_playlist_counts(db, playlist_ids)
        liked_ids = _bulk_liked_playlist_ids(db, playlist_ids, current_user.id)

        playlists = [
            PlaylistSearchResult(
                playlist=_playlist_to_search_response(db, playlist, current_user, counts, liked_ids)
            )
            for playlist in playlist_list
        ]

    return SearchResults(
        query=query,
        users=users,
        songs=songs,
        playlists=playlists,
        total_users=total_users,
        total_songs=total_songs,
        total_playlists=total_playlists
    )
