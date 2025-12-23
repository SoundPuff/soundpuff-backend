from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CommentLikeBase(BaseModel):
    comment_id: int


class CommentLikeCreate(CommentLikeBase):
    pass


class CommentLikeInDB(CommentLikeBase):
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class CommentLike(CommentLikeInDB):
    pass