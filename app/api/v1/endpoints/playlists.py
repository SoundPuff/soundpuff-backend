from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from typing import List, Optional
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from typing import List

from app.core.deps import get_current_user, get_current_user_optional
from app.core.sanitize import sanitize_text
from app.core.config import settings
from app.db.session import get_db
from app.models import User, Playlist, Like, Comment, Follow
from app.schemas.playlist import Playlist as PlaylistSchema, PlaylistCreate, PlaylistUpdate
from app.schemas.playlist import PlaylistAddSong
from app.models import Song
from app.schemas.like import Like as LikeSchema
from app.schemas.comment import Comment as CommentSchema, CommentCreate, CommentUpdate

router = APIRouter()

def _ensure_playlist_accessible(playlist: Playlist, current_user: Optional[User]):
    if playlist.privacy == "private" and (current_user is None or playlist.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )


def _normalize_privacy(playlist: Playlist):
    """Ensure `playlist.privacy` is a string of either 'public' or 'private'.

    Some legacy rows may store privacy as booleans, ints (0/1), or other
    variants; normalize those to the expected literal strings so Pydantic
    validation succeeds.
    """
    try:
        priv = playlist.privacy
    except Exception:
        return playlist

    # If already valid string, keep it
    if isinstance(priv, str):
        s = priv.strip().lower()
        if s in ("public", "private"):
            playlist.privacy = s
            return playlist
        if s in ("true", "t", "1", "yes"):
            playlist.privacy = "public"
            return playlist
        if s in ("false", "f", "0", "no"):
            playlist.privacy = "private"
            return playlist
        # Unexpected string - fallthrough to default

    # Convert booleans and numeric values
    if isinstance(priv, bool):
        playlist.privacy = "public" if priv else "private"
    elif isinstance(priv, (int, float)):
        playlist.privacy = "public" if int(priv) != 0 else "private"
    elif priv is None:
        playlist.privacy = "public"
    else:
        # Last resort default
        playlist.privacy = "public"
    return playlist


@router.get("/", response_model=List[PlaylistSchema])
def read_playlists(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    query = db.query(Playlist)

    if current_user is None:
        query = query.filter(Playlist.privacy == "public")
    else:
        query = query.filter(or_(Playlist.privacy == "public", Playlist.user_id == current_user.id))

    playlists = query.order_by(desc(Playlist.created_at)).offset(skip).limit(limit).all()
    for p in playlists:
        _normalize_privacy(p)
    return playlists


@router.get("/feed", response_model=List[PlaylistSchema])
def read_feed(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get playlists from followed users
    following_ids = db.query(Follow.following_id).filter(
        Follow.follower_id == current_user.id
    ).all()
    following_ids = [f[0] for f in following_ids]
    

    if not following_ids:
        return []

    playlists = db.query(Playlist).filter(
        Playlist.user_id.in_(following_ids)
    ).filter(
        or_(Playlist.privacy == "public", Playlist.user_id == current_user.id)
    ).order_by(desc(Playlist.created_at)).offset(skip).limit(limit).all()

    for p in playlists:
        _normalize_privacy(p)
    return playlists


@router.post("/", response_model=PlaylistSchema, status_code=status.HTTP_201_CREATED)
def create_playlist(
    playlist_in: PlaylistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    title = sanitize_text(playlist_in.title, settings.PLAYLIST_TITLE_MAX_LENGTH)
    description = sanitize_text(playlist_in.description, settings.PLAYLIST_DESCRIPTION_MAX_LENGTH)
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Playlist title is required")

    # Validate song_ids if provided
    songs_to_add = []
    if playlist_in.song_ids:
        # Remove duplicates while preserving order
        unique_song_ids = list(dict.fromkeys(playlist_in.song_ids))
        
        # Fetch and validate all songs exist
        songs_to_add = db.query(Song).filter(Song.id.in_(unique_song_ids)).all()
        found_ids = {song.id for song in songs_to_add}
        missing_ids = [sid for sid in unique_song_ids if sid not in found_ids]
        
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Songs not found: {missing_ids}"
            )

    playlist = Playlist(
        title=title,
        description=description,
        privacy=playlist_in.privacy,
        user_id=current_user.id
    )
    db.add(playlist)
    
    # Add songs to playlist if provided
    if songs_to_add:
        playlist.songs.extend(songs_to_add)
    
    db.commit()
    db.refresh(playlist)
    _normalize_privacy(playlist)
    return playlist


@router.get("/{playlist_id}", response_model=PlaylistSchema)
def read_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )
    _ensure_playlist_accessible(playlist, current_user)
    _normalize_privacy(playlist)
    return playlist


@router.put("/{playlist_id}", response_model=PlaylistSchema)
def update_playlist(
    playlist_id: int,
    playlist_in: PlaylistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )

    # Check ownership
    if playlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this playlist"
        )

    # Update fields
    if playlist_in.title is not None:
        new_title = sanitize_text(playlist_in.title, settings.PLAYLIST_TITLE_MAX_LENGTH)
        if not new_title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Playlist title is required")
        playlist.title = new_title
    if playlist_in.description is not None:
        playlist.description = sanitize_text(playlist_in.description, settings.PLAYLIST_DESCRIPTION_MAX_LENGTH)
    if playlist_in.privacy is not None:
        playlist.privacy = playlist_in.privacy
    # Removed cover image handling (no longer supported)

    db.commit()
    db.refresh(playlist)
    _normalize_privacy(playlist)
    return playlist


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )

    # Check ownership
    if playlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this playlist"
        )

    db.delete(playlist)
    db.commit()
    return None


@router.post("/{playlist_id}/like", response_model=LikeSchema, status_code=status.HTTP_201_CREATED)
def like_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if playlist exists
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )
    _ensure_playlist_accessible(playlist, current_user)
    # Check if already liked
    existing_like = db.query(Like).filter(
        Like.user_id == current_user.id,
        Like.playlist_id == playlist_id
    ).first()

    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already liked this playlist"
        )

    # Create like
    like = Like(user_id=current_user.id, playlist_id=playlist_id)
    db.add(like)
    try:
        db.commit()
        db.refresh(like)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already liked this playlist"
        )
    return like


@router.delete("/{playlist_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def unlike_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find and delete like
    like = db.query(Like).filter(
        Like.user_id == current_user.id,
        Like.playlist_id == playlist_id
    ).first()

    if not like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Like not found"
        )

    db.delete(like)
    db.commit()
    return None


@router.get("/{playlist_id}/comments", response_model=List[CommentSchema])
def read_playlist_comments(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )

    _ensure_playlist_accessible(playlist, current_user)
    comments = db.query(Comment).filter(
        Comment.playlist_id == playlist_id
    ).order_by(desc(Comment.created_at)).all()
    return comments


@router.post("/{playlist_id}/comments", response_model=CommentSchema, status_code=status.HTTP_201_CREATED)
def create_comment(
    playlist_id: int,
    comment_in: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if playlist exists
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )
    
    _ensure_playlist_accessible(playlist, current_user)

    comment_body = sanitize_text(comment_in.body, settings.COMMENT_MAX_LENGTH)
    if not comment_body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment body is required")

    comment = Comment(
        body=comment_body,
        user_id=current_user.id,
        playlist_id=playlist_id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.post("/{playlist_id}/songs", response_model=PlaylistSchema, status_code=status.HTTP_201_CREATED)
def add_song_to_playlist(
    playlist_id: int,
    payload: PlaylistAddSong,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if playlist exists
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )

    # Only playlist owner may add songs
    if playlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add songs to this playlist"
        )

    # Check if song exists
    song = db.query(Song).filter(Song.id == payload.song_id).first()
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found"
        )

    # Check for duplicates
    if any(s.id == song.id for s in playlist.songs):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Song already in playlist"
        )

    # Add song to playlist
    playlist.songs.append(song)
    db.commit()
    db.refresh(playlist)
    _normalize_privacy(playlist)
    return playlist


@router.delete("/{playlist_id}/songs/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_song_from_playlist(
    playlist_id: int,
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if playlist exists
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )

    # Only playlist owner may remove songs
    if playlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to remove songs from this playlist"
        )

    # Check if song is in the playlist
    song = next((s for s in playlist.songs if s.id == song_id), None)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song not found in playlist"
        )

    # Remove song
    playlist.songs.remove(song)
    db.commit()
    return None


@router.put("/comments/{comment_id}", response_model=CommentSchema)
def update_comment(
    comment_id: int,
    comment_in: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    # Check ownership
    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this comment"
        )

    sanitized_body = sanitize_text(comment_in.body, settings.COMMENT_MAX_LENGTH)
    if not sanitized_body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment body is required")

    comment.body = sanitized_body
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    # Check ownership
    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this comment"
        )

    db.delete(comment)
    db.commit()
    return None
