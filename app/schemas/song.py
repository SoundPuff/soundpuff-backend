from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SongBase(BaseModel):
    title: str
    artist: str
    album: Optional[str] = None
    duration: Optional[int] = None
    spotify_id: Optional[str] = None
    preview_url: Optional[str] = None
    cover_image_url: Optional[str] = None


class SongCreate(SongBase):
    pass


class SongInDB(SongBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Song(SongInDB):
    pass
