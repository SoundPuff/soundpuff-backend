from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class LikeBase(BaseModel):
    playlist_id: int


class LikeCreate(LikeBase):
    pass


class LikeInDB(LikeBase):
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class Like(LikeInDB):
    pass


class SongLikeBase(BaseModel):
    song_id: int


class SongLikeCreate(SongLikeBase):
    pass


class SongLikeInDB(SongLikeBase):
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class SongLike(SongLikeInDB):
    pass
