from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User, Playlist, Like, Comment, Follow
from app.schemas.playlist import Playlist as PlaylistSchema, PlaylistCreate, PlaylistUpdate
from app.schemas.like import Like as LikeSchema
from app.schemas.comment import Comment as CommentSchema, CommentCreate, CommentUpdate

router = APIRouter()


@router.get("/", response_model=List[PlaylistSchema])
def read_playlists(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    playlists = db.query(Playlist).order_by(desc(Playlist.created_at)).offset(skip).limit(limit).all()
    return playlists


@router.get("/feed", response_model=List[PlaylistSchema])
def read_feed(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get playlists from followed users
    following_ids = db.query(Follow.followed_id).filter(Follow.follower_id == current_user.id).all()
    following_ids = [f[0] for f in following_ids]

    playlists = db.query(Playlist).filter(
        Playlist.owner_id.in_(following_ids)
    ).order_by(desc(Playlist.created_at)).offset(skip).limit(limit).all()

    return playlists


@router.post("/", response_model=PlaylistSchema, status_code=status.HTTP_201_CREATED)
def create_playlist(
    playlist_in: PlaylistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    playlist = Playlist(
        **playlist_in.dict(),
        user_id=current_user.id
    )
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return playlist


@router.get("/{playlist_id}", response_model=PlaylistSchema)
def read_playlist(playlist_id: int, db: Session = Depends(get_db)):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )
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
        playlist.title = playlist_in.title
    if playlist_in.description is not None:
        playlist.description = playlist_in.description
    if playlist_in.cover_image_url is not None:
        playlist.cover_image_url = playlist_in.cover_image_url

    db.commit()
    db.refresh(playlist)
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
    db.commit()
    db.refresh(like)
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
def read_playlist_comments(playlist_id: int, db: Session = Depends(get_db)):
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

    comment = Comment(
        content=comment_in.content,
        user_id=current_user.id,
        playlist_id=playlist_id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


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

    comment.content = comment_in.content
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
