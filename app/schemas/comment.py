from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.schemas.user import User


class CommentBase(BaseModel):
    body: str
    parent_comment_id: Optional[int] = None


class CommentCreate(CommentBase):
    pass


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
    replies: List["Comment"] = Field(default_factory=list)
    likes_count: int = 0
    is_liked: bool = False

Comment.model_rebuild()
