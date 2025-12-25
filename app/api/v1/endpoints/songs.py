from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import desc, or_, func
from sqlalchemy.orm import Session, selectinload
from typing import Optional, List

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Song, User, Playlist, Like, SongLike
from app.schemas.like import SongLike as SongLikeSchema
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
    return db.query(Like).filter(
        Like.user_id == user_id,
        Like.playlist_id == playlist_id
    ).first() is not None


def _check_user_liked_song(db: Session, song_id: int, user_id) -> bool:
    """Check if a user has liked a specific song."""
    if user_id is None:
        return False
    return db.query(SongLike).filter(
        SongLike.user_id == user_id,
        SongLike.song_id == song_id
    ).first() is not None


def _prefetch_song_stats(
    db: Session,
    songs: List[Song],
    current_user: Optional[User],
    prefetch_is_liked: bool = True,
) -> None:
    """Annotate songs with bulk-fetched counts and liked state."""
    song_ids = [s.id for s in songs]
    if not song_ids:
        return

    likes_counts = dict(
        db.query(SongLike.song_id, func.count(SongLike.song_id))
        .filter(SongLike.song_id.in_(song_ids))
        .group_by(SongLike.song_id)
        .all()
    )

    liked_ids = set()
    if prefetch_is_liked and current_user is not None:
        liked_ids = {
            sid
            for (sid,) in db.query(SongLike.song_id)
            .filter(
                SongLike.user_id == current_user.id,
                SongLike.song_id.in_(song_ids),
            )
            .all()
        }

    for song in songs:
        song._prefetched_likes_count = int(likes_counts.get(song.id, 0))
        if prefetch_is_liked:
            song._prefetched_is_liked = song.id in liked_ids


def _song_to_response(db: Session, song: Song, current_user: Optional[User], include_is_liked: bool = True) -> dict:
    """Convert a song model to a response dict with is_liked."""
    pre_likes_count = getattr(song, "_prefetched_likes_count", None)

    res = {
        "id": song.id,
        "title": song.title,
        "artist": song.artist,
        "album_art_url": song.album_art_url,
        "song_url": song.song_url,
        "created_at": song.created_at,
        "likes_count": int(pre_likes_count) if pre_likes_count is not None else song.likes_count,
    }

    if include_is_liked:
        pre_is_liked = getattr(song, "_prefetched_is_liked", None)
        is_liked = (
            bool(pre_is_liked)
            if pre_is_liked is not None
            else _check_user_liked_song(db, song.id, current_user.id if current_user else None)
        )
        res["is_liked"] = is_liked
    
    return res


def _playlist_to_search_response(db: Session, playlist: Playlist, current_user: User, include_is_liked: bool = True) -> dict:
    """Convert a playlist model to a search response dict with is_liked."""
    res = {
        "id": playlist.id,
        "title": playlist.title,
        "description": playlist.description,
        "privacy": playlist.privacy,
        "cover_image_url": playlist.cover_image_url,
        "user_id": playlist.user_id,
        "created_at": playlist.created_at,
        "updated_at": playlist.updated_at,
        "owner": playlist.owner,
        "songs": [_song_to_response(db, s, current_user, include_is_liked=include_is_liked) for s in (playlist.songs or [])],
        "likes_count": playlist.likes_count,
        "comments_count": playlist.comments_count,
    }

    if include_is_liked:
        res["is_liked"] = _check_user_liked_playlist(db, playlist.id, current_user.id)
    
    return res


# ==================== SONG SEARCH ====================

@router.get("/search", response_model=SongSearchResults, response_model_exclude_none=True)
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

    _prefetch_song_stats(db, songs, current_user, prefetch_is_liked=False)

    song_results = [
        SongSearchResult(song=_song_to_response(db, song, current_user, include_is_liked=False)) 
        for song in songs
    ]

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

@router.get("/playlists/search", response_model=PlaylistSearchResults, response_model_exclude_none=True)
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

    base_query = db.query(Playlist).filter(search_filter).options(
        selectinload(Playlist.owner),
        selectinload(Playlist.songs)
    )

    # Show public + user's own private playlists
    base_query = base_query.filter(
        or_(
            Playlist.privacy == "public",
            Playlist.user_id == current_user.id
        )
    )

    total = base_query.count()

    playlists = (
        base_query.order_by(desc(Playlist.created_at)).offset(offset).limit(limit).all()
    )

    # Prefetch song stats for all songs in these playlists
    all_songs = []
    for p in playlists:
        all_songs.extend(p.songs)
    _prefetch_song_stats(db, all_songs, current_user, prefetch_is_liked=False)

    playlist_results = [
        PlaylistSearchResult(playlist=_playlist_to_search_response(db, playlist, current_user, include_is_liked=False)) 
        for playlist in playlists
    ]

    return PlaylistSearchResults(query=query, playlists=playlist_results, total=total)


# ==================== COMBINED SEARCH ====================

@router.get("/all", response_model=SearchResults, response_model_exclude_none=True)
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
        _prefetch_song_stats(db, song_list, current_user, prefetch_is_liked=False)
        songs = [
            SongSearchResult(song=_song_to_response(db, song, current_user, include_is_liked=False)) 
            for song in song_list
        ]

    # Search Playlists
    if type in (SearchType.ALL, SearchType.PLAYLISTS):
        playlist_filter = or_(
            Playlist.title.ilike(f"%{query}%"),
            Playlist.description.ilike(f"%{query}%"),
        )
        playlist_query = db.query(Playlist).filter(playlist_filter).options(
            selectinload(Playlist.owner),
            selectinload(Playlist.songs)
        )
        
        # Show public + user's own private playlists
        playlist_query = playlist_query.filter(
            or_(
                Playlist.privacy == "public",
                Playlist.user_id == current_user.id
            )
        )
        
        total_playlists = playlist_query.count()
        playlist_list = playlist_query.order_by(desc(Playlist.created_at)).offset(offset).limit(limit).all()
        
        # Prefetch song stats for all songs in these playlists
        all_playlist_songs = []
        for p in playlist_list:
            all_playlist_songs.extend(p.songs)
        _prefetch_song_stats(db, all_playlist_songs, current_user, prefetch_is_liked=False)

        playlists = [
            PlaylistSearchResult(playlist=_playlist_to_search_response(db, playlist, current_user, include_is_liked=False)) 
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


# ==================== SONG LIKES ====================

@router.post("/{song_id}/like", response_model=SongLikeSchema, status_code=status.HTTP_201_CREATED)
def like_song(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Like a song.
    Requires authentication.
    """
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found"
        )

    existing_like = db.query(SongLike).filter(
        SongLike.user_id == current_user.id,
        SongLike.song_id == song_id
    ).first()

    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already liked this song"
        )

    like = SongLike(user_id=current_user.id, song_id=song_id)
    db.add(like)
    db.commit()
    db.refresh(like)
    return like


@router.delete("/{song_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def unlike_song(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unlike a song.
    Requires authentication.
    """
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found"
        )

    like = db.query(SongLike).filter(
        SongLike.user_id == current_user.id,
        SongLike.song_id == song_id
    ).first()

    if not like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Like not found"
        )

    db.delete(like)
    db.commit()
    return None
