from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models import Playlist, Song, User
from app.schemas.song import Song as SongSchema, SongListResponse
from app.schemas.search import (
    
    PlaylistSearchResult,
    PlaylistSearchResults,
    SearchResults,
    SearchType,
    SongSearchResult,
    SongSearchResults,
    UserSearchResult,
    UserSearchResults,
)


router = APIRouter()

# ==================== SONGS ====================


@router.get("/", response_model=SongListResponse)
def read_songs(
    skip: int = Query(0, ge=0, description="Number of songs to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of songs to return"),
    db: Session = Depends(get_db),
):
    """Return a paginated list of songs ordered by newest first."""

    base_query = db.query(Song).order_by(desc(Song.created_at))
    total = base_query.count()
    songs = base_query.offset(skip).limit(limit).all()

    return SongListResponse(total=total, songs=songs)


@router.get("/{song_id}", response_model=SongSchema)
def read_song(
    song_id: int,
    db: Session = Depends(get_db),
):
    """Fetch a single song by its id."""

    song = db.query(Song).filter(Song.id == song_id).first()

    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found",
        )

    return song



# ==================== SONG SEARCH ====================

@router.get("/search", response_model=SongSearchResults)
def search_songs(
    query: str = Query(..., min_length=1, description="Search query for song title or artist"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Search songs by title or artist using a case-insensitive partial match.
    Authentication is optional.
    
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

    base_query = db.query(Playlist).filter(search_filter)

    # Show public + user's own private playlists
    base_query = base_query.filter(
        or_(
            Playlist.privacy == "public",
            Playlist.user_id == current_user.id,
        )
    )

    total = base_query.count()

    playlists = (
        base_query.order_by(desc(Playlist.created_at)).offset(offset).limit(limit).all()
    )

    playlist_results = [PlaylistSearchResult(playlist=playlist) for playlist in playlists]

    return PlaylistSearchResults(query=query, playlists=playlist_results, total=total)


# ==================== COMBINED SEARCH ====================

@router.get("/all", response_model=SearchResults)
def search_all(
    query: str = Query(..., min_length=1, description="Search query"),
    type: SearchType = Query(
        SearchType.ALL, description="Type of search: all, users, songs, or playlists"
    ),
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
        user_list = (
            user_query.order_by(desc(User.created_at)).offset(offset).limit(limit).all()
        )
        users = [UserSearchResult(user=user) for user in user_list]

    # Search Songs
    if type in (SearchType.ALL, SearchType.SONGS):
        song_filter = or_(
            Song.title.ilike(f"%{query}%"),
            Song.artist.ilike(f"%{query}%"),
        )
        song_query = db.query(Song).filter(song_filter)
        total_songs = song_query.count()
        song_list = (
            song_query.order_by(desc(Song.created_at)).offset(offset).limit(limit).all()
        )
        songs = [SongSearchResult(song=song) for song in song_list]

    # Search Playlists
    if type in (SearchType.ALL, SearchType.PLAYLISTS):
        playlist_filter = or_(
            Playlist.title.ilike(f"%{query}%"),
            Playlist.description.ilike(f"%{query}%"),
        )
        playlist_query = db.query(Playlist).filter(playlist_filter)
        
        # Show public + user's own private playlists
        playlist_query = playlist_query.filter(
            or_(Playlist.privacy == "public", Playlist.user_id == current_user.id)
        )
        
        total_playlists = playlist_query.count()
        playlist_list = (
            playlist_query.order_by(desc(Playlist.created_at)).offset(offset).limit(limit).all()
        )
        playlists = [PlaylistSearchResult(playlist=playlist) for playlist in playlist_list]

    return SearchResults(
        query=query,
        users=users,
        songs=songs,
        playlists=playlists,
        total_users=total_users,
        total_songs=total_songs,
        total_playlists=total_playlists,
    )