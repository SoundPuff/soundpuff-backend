from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User, Follow
from app.schemas.user import User as UserSchema, UserUpdate
# Note: Follow schema is not needed for 204 responses

router = APIRouter()


@router.get("/me", response_model=UserSchema)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserSchema)
def update_current_user(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if user_in.bio is not None:
        current_user.bio = user_in.bio
    if user_in.avatar_url is not None:
        current_user.avatar_url = user_in.avatar_url

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/{username}", response_model=UserSchema)
def read_user_by_username(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post("/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
def follow_user(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get user to follow
    user_to_follow = db.query(User).filter(User.username == username).first()
    if not user_to_follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if trying to follow self
    if user_to_follow.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself"
        )

    # Check if already following
    existing_follow = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id == user_to_follow.id
    ).first()

    if existing_follow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already following this user"
        )

    # Create follow relationship
    follow = Follow(
        follower_id=current_user.id,
        following_id=user_to_follow.id
    )
    db.add(follow)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_user(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get user to unfollow
    user_to_unfollow = db.query(User).filter(User.username == username).first()
    if not user_to_unfollow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Find and delete follow relationship
    follow = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id == user_to_unfollow.id
    ).first()

    if not follow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not following this user"
        )

    db.delete(follow)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{username}/followers", response_model=List[UserSchema])
def get_user_followers(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    followers = db.query(User).join(Follow, Follow.follower_id == User.id).filter(
        Follow.following_id == user.id
    ).all()
    return followers


@router.get("/{username}/following", response_model=List[UserSchema])
def get_user_following(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    following = db.query(User).join(Follow, Follow.following_id == User.id).filter(
        Follow.follower_id == user.id
    ).all()
    return following
