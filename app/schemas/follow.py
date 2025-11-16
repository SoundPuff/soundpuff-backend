from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class FollowBase(BaseModel):
    following_id: UUID


class FollowCreate(FollowBase):
    pass


class FollowInDB(FollowBase):
    follower_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class Follow(FollowInDB):
    pass
