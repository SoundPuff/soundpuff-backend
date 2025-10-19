from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.user import User


class CommentBase(BaseModel):
    content: str


class CommentCreate(CommentBase):
    playlist_id: int


class CommentUpdate(BaseModel):
    content: str


class CommentInDB(CommentBase):
    id: int
    user_id: int
    playlist_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Comment(CommentInDB):
    user: User
