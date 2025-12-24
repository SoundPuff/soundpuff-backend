from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from typing import Literal


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    """Schema for creating a user profile after Supabase Auth signup"""
    pass


class UserUpdate(BaseModel):
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserInDB(UserBase):
    id: UUID
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _anonymize_deleted_user(cls, data):
        # When FastAPI builds response models from ORM objects, `data` may be the
        # SQLAlchemy instance itself (from_attributes=True). Rewrite deleted users
        # to a stable, non-identifying public representation.
        try:
            is_deleted = getattr(data, "is_deleted", False)
        except Exception:
            is_deleted = False

        if not is_deleted:
            return data

        # Convert to a plain dict so Pydantic doesn't read original attributes.
        return {
            "id": getattr(data, "id"),
            "username": "Deleted user",
            "bio": None,
            "avatar_url": None,
            "created_at": getattr(data, "created_at"),
        }

    class Config:
        from_attributes = True


class User(UserInDB):
    pass


class PlaylistBrief(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    privacy: Literal["public", "private"]
    cover_image_url: Optional[str] = None
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    owner: User
    likes_count: int = 0
    comments_count: int = 0
    is_liked: bool = False

    class Config:
        from_attributes = True


class UserWithPlaylists(User):
    playlists: List[PlaylistBrief] = Field(default_factory=list)
