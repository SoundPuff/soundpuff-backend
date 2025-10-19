from pydantic import BaseModel
from datetime import datetime


class FollowBase(BaseModel):
    followed_id: int


class FollowCreate(FollowBase):
    pass


class FollowInDB(FollowBase):
    id: int
    follower_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Follow(FollowInDB):
    pass
