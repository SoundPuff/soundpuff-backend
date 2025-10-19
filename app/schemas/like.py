from pydantic import BaseModel
from datetime import datetime


class LikeBase(BaseModel):
    playlist_id: int


class LikeCreate(LikeBase):
    pass


class LikeInDB(LikeBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Like(LikeInDB):
    pass
