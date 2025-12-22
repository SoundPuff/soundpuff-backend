from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


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
