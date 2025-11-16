from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.schemas.user import User


class CommentBase(BaseModel):
    body: str


class CommentCreate(CommentBase):
    playlist_id: int


class CommentUpdate(BaseModel):
    body: str


class CommentInDB(CommentBase):
    id: int
    user_id: UUID
    playlist_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Comment(CommentInDB):
    user: User
